package leader

import (
	"bufio"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"
)

var (
	DataDir        = os.Getenv("DATA_DIR")
	FlushInterval  = 3600
)

func init() {
	if DataDir == "" {
		DataDir = "data"
	}
}

func datePath(d time.Time) string {
	return filepath.Join(DataDir, fmt.Sprintf("%04d", d.Year()), fmt.Sprintf("%02d", d.Month()), fmt.Sprintf("%02d.json", d.Day()))
}

func AppendResults(results []CheckResultWithNode) {
	if len(results) == 0 {
		return
	}

	byDate := make(map[string][]CheckResultWithNode)
	for _, r := range results {
		day := time.Unix(int64(r.Timestamp), 0).Format("2006-01-02")
		byDate[day] = append(byDate[day], r)
	}

	for dayStr, items := range byDate {
		t, err := time.Parse("2006-01-02", dayStr)
		if err != nil {
			log.Printf("Error parsing date %s: %v", dayStr, err)
			continue
		}
		path := datePath(t)
		dir := filepath.Dir(path)
		if err := os.MkdirAll(dir, 0755); err != nil {
			log.Printf("Error creating directory %s: %v", dir, err)
			continue
		}
		f, err := os.OpenFile(path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		if err != nil {
			log.Printf("Error opening file %s: %v", path, err)
			continue
		}
		enc := json.NewEncoder(f)
		for _, item := range items {
			if err := enc.Encode(item); err != nil {
				log.Printf("Error encoding result to %s: %v", path, err)
			}
		}
		f.Close()
	}
}

func ReadResults(start, end time.Time) []CheckResultWithNode {
	var results []CheckResultWithNode
	current := start
	for !current.After(end) {
		path := datePath(current)
		if _, err := os.Stat(path); err == nil {
			f, err := os.Open(path)
			if err != nil {
				log.Printf("Error opening file %s: %v", path, err)
				current = current.Add(24 * time.Hour)
				continue
			}
			scanner := bufio.NewScanner(f)
			for scanner.Scan() {
				line := strings.TrimSpace(scanner.Text())
				if line == "" {
					continue
				}
				var r CheckResultWithNode
				if err := json.Unmarshal([]byte(line), &r); err != nil {
					log.Printf("Skipping malformed JSON in %s: %s", path, line[:min(len(line), 80)])
					continue
				}
				results = append(results, r)
			}
			f.Close()
		}
		current = current.Add(24 * time.Hour)
	}
	return results
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func LoadIntoMemory(resultsStore *ResultsStore) {
	cutoff := time.Now().Add(-90 * 24 * time.Hour)
	end := time.Now()
	raw := ReadResults(cutoff, end)

	sort.Slice(raw, func(i, j int) bool {
		return raw[i].Timestamp > raw[j].Timestamp
	})

	resultsStore.mu.Lock()
	defer resultsStore.mu.Unlock()

	cutoff90h := time.Now().Add(-90 * time.Hour).Unix()

	for _, r := range raw {
		if r.NodeIP == "" {
			continue
		}
		check := CheckResult{
			TargetIP:  r.TargetIP,
			PingOK:    r.PingOK,
			HTTPOK:    r.HTTPOK,
			Timestamp: r.Timestamp,
			LatencyMs: r.LatencyMs,
		}
		if r.Timestamp >= float64(cutoff90h) {
			resultsStore.results[r.NodeIP] = append(resultsStore.results[r.NodeIP], check)
		} else {
			day := time.Unix(int64(r.Timestamp), 0).Format("2006-01-02")
			if resultsStore.dayAggregates[day] == nil {
				resultsStore.dayAggregates[day] = make(map[string]*ConnectionStats)
			}
			key := r.NodeIP + "\x00" + r.TargetIP
			if resultsStore.dayAggregates[day][key] == nil {
				resultsStore.dayAggregates[day][key] = &ConnectionStats{}
			}
			resultsStore.dayAggregates[day][key].TotalChecks++
			if r.PingOK {
				resultsStore.dayAggregates[day][key].PingOK++
			}
			if r.HTTPOK {
				resultsStore.dayAggregates[day][key].HTTPOK++
			}
		}
	}
}

func FlushLoop(store *ResultsStore, interval time.Duration, stop <-chan struct{}) {
	for {
		select {
		case <-stop:
			return
		case <-time.After(interval):
			flushOnce(store)
		}
	}
}

func flushOnce(store *ResultsStore) {
	store.mu.Lock()
	defer store.mu.Unlock()

	if len(store.results) == 0 {
		return
	}

	var batch []CheckResultWithNode
	for nodeIP, checks := range store.results {
		for _, c := range checks {
			batch = append(batch, CheckResultWithNode{
				NodeIP:    nodeIP,
				TargetIP:  c.TargetIP,
				PingOK:    c.PingOK,
				HTTPOK:    c.HTTPOK,
				Timestamp: c.Timestamp,
				LatencyMs: c.LatencyMs,
			})
		}
	}

	AppendResults(batch)
	log.Printf("Flushed %d results to disk", len(batch))

	cutoff90h := time.Now().Add(-90 * time.Hour).Unix()
	for nodeIP := range store.results {
		var recent []CheckResult
		for _, c := range store.results[nodeIP] {
			if c.Timestamp >= float64(cutoff90h) {
				recent = append(recent, c)
			} else {
				day := time.Unix(int64(c.Timestamp), 0).Format("2006-01-02")
				if store.dayAggregates[day] == nil {
					store.dayAggregates[day] = make(map[string]*ConnectionStats)
				}
				key := nodeIP + "\x00" + c.TargetIP
				if store.dayAggregates[day][key] == nil {
					store.dayAggregates[day][key] = &ConnectionStats{}
				}
				store.dayAggregates[day][key].TotalChecks++
				if c.PingOK {
					store.dayAggregates[day][key].PingOK++
				}
				if c.HTTPOK {
					store.dayAggregates[day][key].HTTPOK++
				}
			}
		}
		if len(recent) > 0 {
			store.results[nodeIP] = recent
		} else {
			delete(store.results, nodeIP)
		}
	}
}

var (
	flushStopOnce sync.Once
	stopFlush     chan struct{}
)

func StartFlushLoop(store *ResultsStore) {
	stopFlush = make(chan struct{})
	go FlushLoop(store, time.Duration(FlushInterval)*time.Second, stopFlush)
}

func StopFlushLoop() {
	if stopFlush != nil {
		close(stopFlush)
	}
}
