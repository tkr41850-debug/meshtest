package leader

import (
	"math"
	"sync"
	"time"
)

type ResultsStore struct {
	mu            sync.RWMutex
	results       map[string][]CheckResult
	dayAggregates map[string]map[string]*ConnectionStats
}

func NewResultsStore() *ResultsStore {
	return &ResultsStore{
		results:       make(map[string][]CheckResult),
		dayAggregates: make(map[string]map[string]*ConnectionStats),
	}
}

func (s *ResultsStore) Add(nodeIP string, checks []CheckResult, timestamp float64) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.results[nodeIP] = append(s.results[nodeIP], checks...)
}

func (s *ResultsStore) GetRaw() map[string][]CheckResult {
	s.mu.RLock()
	defer s.mu.RUnlock()
	result := make(map[string][]CheckResult, len(s.results))
	for k, v := range s.results {
		cp := make([]CheckResult, len(v))
		copy(cp, v)
		result[k] = cp
	}
	return result
}

type QueryResult90m struct {
	Window    string       `json:"window"`
	Checks    []CheckResultWithNode `json:"checks"`
	Statuses  []StatusInfo `json:"statuses"`
	Timestamp float64      `json:"timestamp"`
}

type CheckResultWithNode struct {
	NodeIP   string  `json:"node_ip"`
	TargetIP string  `json:"target_ip"`
	PingOK   bool    `json:"ping_ok"`
	HTTPOK   bool    `json:"http_ok"`
	Timestamp float64 `json:"timestamp"`
	LatencyMs float64 `json:"latency_ms,omitempty"`
	IsExtra   bool    `json:"is_extra,omitempty"`
}

func (s *ResultsStore) Query90m(registry *Registry) QueryResult90m {
	now := float64(time.Now().Unix())
	cutoff := now - 5400
	s.mu.RLock()
	defer s.mu.RUnlock()

	checks := make([]CheckResultWithNode, 0)
	for nodeIP, nodeResults := range s.results {
		for _, r := range nodeResults {
			if r.Timestamp >= cutoff {
			checks = append(checks, CheckResultWithNode{
				NodeIP:    nodeIP,
				TargetIP:  r.TargetIP,
				PingOK:    r.PingOK,
				HTTPOK:    r.HTTPOK,
				Timestamp: r.Timestamp,
				LatencyMs: r.LatencyMs,
				IsExtra:   r.IsExtra,
			})
			}
		}
	}

	allIPs := registry.AllIPs()
	statuses := make([]StatusInfo, 0)
	for _, src := range allIPs {
		for _, dst := range allIPs {
			if src != dst {
				pingOK := checkPairStatus(s.results, src, dst, cutoff, "ping")
				httpOK := checkPairStatus(s.results, src, dst, cutoff, "http")
				statuses = append(statuses,
					StatusInfo{SrcIP: src, DstIP: dst, Type: "ping", OK: pingOK},
					StatusInfo{SrcIP: src, DstIP: dst, Type: "http", OK: httpOK},
				)
			}
		}
	}

	return QueryResult90m{
		Window:    "90m",
		Checks:    checks,
		Statuses:  statuses,
		Timestamp: now,
	}
}

func checkPairStatus(results map[string][]CheckResult, srcIP, dstIP string, cutoff float64, checkType string) bool {
	nodeResults, ok := results[srcIP]
	if !ok {
		return false
	}
	for _, c := range nodeResults {
		if c.IsExtra {
			continue
		}
		if c.TargetIP == dstIP && c.Timestamp >= cutoff {
			if checkType == "ping" && c.PingOK {
				return true
			}
			if checkType == "http" && c.HTTPOK {
				return true
			}
		}
	}
	return false
}

type QueryResult90h struct {
	Window    string      `json:"window"`
	Hours     []HourEntry `json:"hours"`
	Timestamp float64     `json:"timestamp"`
}

func (s *ResultsStore) Query90h() QueryResult90h {
	now := float64(time.Now().Unix())
	start := now - 90*3600
	s.mu.RLock()
	defer s.mu.RUnlock()

	byHour := make(map[string]map[string]*ConnectionStats)
	for nodeIP, nodeResults := range s.results {
		for _, r := range nodeResults {
			if r.Timestamp < start {
				continue
			}
			hour := time.Unix(int64(r.Timestamp), 0).Format("2006-01-02T15:00")
			if byHour[hour] == nil {
				byHour[hour] = make(map[string]*ConnectionStats)
			}
			key := nodeIP + "\x00" + r.TargetIP
			if byHour[hour][key] == nil {
				byHour[hour][key] = &ConnectionStats{}
			}
			byHour[hour][key].TotalChecks++
			if r.PingOK {
				byHour[hour][key].PingOK++
			}
			if r.HTTPOK {
				byHour[hour][key].HTTPOK++
			}
		}
	}

	hours := make([]HourEntry, 0)
	for hourStr := range byHour {
		var conns []DayConnection
		for key, stats := range byHour[hourStr] {
			src, dst := splitKey(key)
			conns = append(conns, DayConnection{
				NodeIP:      src,
				TargetIP:    dst,
				TotalChecks: stats.TotalChecks,
				PingOK:      stats.PingOK,
				HTTPOK:      stats.HTTPOK,
				PingUptime:  safePct(stats.PingOK, stats.TotalChecks),
				HTTPUptime:  safePct(stats.HTTPOK, stats.TotalChecks),
			})
		}
		hours = append(hours, HourEntry{Date: hourStr, Connections: conns})
	}

	sortByDate(hours)
	return QueryResult90h{
		Window:    "90h",
		Hours:     hours,
		Timestamp: now,
	}
}

type QueryResult90d struct {
	Window    string     `json:"window"`
	Days      []DayEntry `json:"days"`
	Timestamp float64    `json:"timestamp"`
}

func (s *ResultsStore) Query90d() QueryResult90d {
	now := float64(time.Now().Unix())
	cutoff := now - 90*24*3600
	s.mu.RLock()
	defer s.mu.RUnlock()

	byDay := make(map[string]map[string]*ConnectionStats)

	// Start with day aggregates (historical data from disk)
	for dayStr, dayData := range s.dayAggregates {
		if byDay[dayStr] == nil {
			byDay[dayStr] = make(map[string]*ConnectionStats)
		}
		for key, stats := range dayData {
			byDay[dayStr][key] = &ConnectionStats{
				TotalChecks: stats.TotalChecks,
				PingOK:      stats.PingOK,
				HTTPOK:      stats.HTTPOK,
			}
		}
	}

	// Merge in-memory results
	for nodeIP, nodeResults := range s.results {
		for _, r := range nodeResults {
			if r.Timestamp < cutoff {
				continue
			}
			day := time.Unix(int64(r.Timestamp), 0).Format("2006-01-02")
			if byDay[day] == nil {
				byDay[day] = make(map[string]*ConnectionStats)
			}
			key := nodeIP + "\x00" + r.TargetIP
			if byDay[day][key] == nil {
				byDay[day][key] = &ConnectionStats{}
			}
			byDay[day][key].TotalChecks++
			if r.PingOK {
				byDay[day][key].PingOK++
			}
			if r.HTTPOK {
				byDay[day][key].HTTPOK++
			}
		}
	}

	days := make([]DayEntry, 0)
	for dayStr := range byDay {
		var conns []DayConnection
		for key, stats := range byDay[dayStr] {
			src, dst := splitKey(key)
			conns = append(conns, DayConnection{
				NodeIP:      src,
				TargetIP:    dst,
				TotalChecks: stats.TotalChecks,
				PingOK:      stats.PingOK,
				HTTPOK:      stats.HTTPOK,
				PingUptime:  safePct(stats.PingOK, stats.TotalChecks),
				HTTPUptime:  safePct(stats.HTTPOK, stats.TotalChecks),
			})
		}
		days = append(days, DayEntry{Date: dayStr, Connections: conns})
	}

	sortDaysByDate(days)
	return QueryResult90d{
		Window:    "90d",
		Days:      days,
		Timestamp: now,
	}
}

func safePct(ok, total int) float64 {
	if total == 0 {
		return 0.0
	}
	return math.Round(float64(ok)/float64(total)*1000) / 10
}

func splitKey(key string) (string, string) {
	for i := 0; i < len(key); i++ {
		if key[i] == 0 {
			return key[:i], key[i+1:]
		}
	}
	return key, ""
}

type sortableByDate []struct {
	date string
}

func sortByDate(entries []HourEntry) {
	for i := 0; i < len(entries); i++ {
		for j := i + 1; j < len(entries); j++ {
			if entries[i].Date > entries[j].Date {
				entries[i], entries[j] = entries[j], entries[i]
			}
		}
	}
}

func sortDaysByDate(entries []DayEntry) {
	for i := 0; i < len(entries); i++ {
		for j := i + 1; j < len(entries); j++ {
			if entries[i].Date > entries[j].Date {
				entries[i], entries[j] = entries[j], entries[i]
			}
		}
	}
}
