package leader

import (
	"fmt"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func setupTempDataDir(t *testing.T) string {
	t.Helper()
	dir, err := os.MkdirTemp("", "mesh-test-*")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { os.RemoveAll(dir) })
	oldDir := DataDir
	DataDir = dir
	t.Cleanup(func() { DataDir = oldDir })
	return dir
}

func TestAppendAndReadResults(t *testing.T) {
	setupTempDataDir(t)

	now := float64(time.Now().Unix())
	results := []CheckResultWithNode{
		{NodeIP: "10.0.0.1", TargetIP: "10.0.0.2", PingOK: true, HTTPOK: true, Timestamp: now},
	}

	AppendResults(results)

	start := time.Now().Add(-24 * time.Hour)
	end := time.Now()
	read := ReadResults(start, end)

	if len(read) != 1 {
		t.Fatalf("expected 1 result, got %d", len(read))
	}
	if read[0].NodeIP != "10.0.0.1" {
		t.Errorf("expected node_ip 10.0.0.1, got %s", read[0].NodeIP)
	}
	if read[0].PingOK != true {
		t.Errorf("expected ping_ok true, got false")
	}
}

func TestEmptyReadReturnsEmpty(t *testing.T) {
	setupTempDataDir(t)
	start := time.Now().Add(-24 * time.Hour)
	end := time.Now()
	read := ReadResults(start, end)
	if len(read) != 0 {
		t.Errorf("expected no results, got %d", len(read))
	}
}

func TestAppendPreservesAcrossMultipleCalls(t *testing.T) {
	setupTempDataDir(t)
	now := float64(time.Now().Unix())

	AppendResults([]CheckResultWithNode{
		{NodeIP: "10.0.0.1", TargetIP: "10.0.0.2", PingOK: true, HTTPOK: true, Timestamp: now},
	})
	AppendResults([]CheckResultWithNode{
		{NodeIP: "10.0.0.1", TargetIP: "10.0.0.3", PingOK: false, HTTPOK: true, Timestamp: now},
	})

	read := ReadResults(time.Now().Add(-24*time.Hour), time.Now())
	if len(read) != 2 {
		t.Fatalf("expected 2 results, got %d", len(read))
	}
}

func TestMalformedJSONLineSkippedWithWarning(t *testing.T) {
	dir := setupTempDataDir(t)

	now := float64(time.Now().Unix())
	AppendResults([]CheckResultWithNode{
		{NodeIP: "10.0.0.1", TargetIP: "10.0.0.2", PingOK: true, HTTPOK: true, Timestamp: now},
	})

	badFile := filepath.Join(dir, time.Now().Format("2006/01/02.json"))
	f, err := os.OpenFile(badFile, os.O_APPEND|os.O_WRONLY, 0644)
	if err != nil {
		t.Fatal(err)
	}
	f.WriteString("invalid json\n")
	f.Close()

	read := ReadResults(time.Now().Add(-24*time.Hour), time.Now())
	if len(read) != 1 {
		t.Errorf("expected 1 valid result, got %d", len(read))
	}
}

func TestFlushResults(t *testing.T) {
	setupTempDataDir(t)
	store := NewResultsStore()

	now := float64(time.Now().Unix())
	store.Add("10.0.0.1", []CheckResult{
		{TargetIP: "10.0.0.2", PingOK: true, HTTPOK: true, Timestamp: now},
	}, now)

	flushOnce(store)

	read := ReadResults(time.Now().Add(-24*time.Hour), time.Now())
	if len(read) != 1 {
		t.Errorf("expected 1 flushed result, got %d", len(read))
	}
}

func TestLoadIntoMemory(t *testing.T) {
	setupTempDataDir(t)

	now := float64(time.Now().Unix())
	AppendResults([]CheckResultWithNode{
		{NodeIP: "10.0.0.1", TargetIP: "10.0.0.2", PingOK: true, HTTPOK: true, Timestamp: now},
	})

	store := NewResultsStore()
	LoadIntoMemory(store)

	raw := store.GetRaw()
	if len(raw) != 1 {
		t.Errorf("expected 1 node in memory, got %d", len(raw))
	}
}

func TestLoadIntoMemoryEmptyDataDir(t *testing.T) {
	setupTempDataDir(t)
	store := NewResultsStore()
	LoadIntoMemory(store)
	raw := store.GetRaw()
	if len(raw) != 0 {
		t.Errorf("expected empty store, got %d nodes", len(raw))
	}
}

func TestAppendResultsWritesFileToDisk(t *testing.T) {
	dir := setupTempDataDir(t)

	now := float64(time.Now().Unix())
	AppendResults([]CheckResultWithNode{
		{NodeIP: "10.0.0.1", TargetIP: "10.0.0.2", PingOK: true, HTTPOK: true, Timestamp: now},
	})

	dayPath := filepath.Join(dir, time.Now().Format("2006/01/02.json"))
	if _, err := os.Stat(dayPath); os.IsNotExist(err) {
		t.Errorf("expected file %s to exist on disk after AppendResults", dayPath)
	}
}

func TestFlushResultsWritesFileToDisk(t *testing.T) {
	dir := setupTempDataDir(t)
	lastFlushTimestamp = 0
	store := NewResultsStore()

	now := float64(time.Now().Unix())
	store.Add("10.0.0.1", []CheckResult{
		{TargetIP: "10.0.0.2", PingOK: true, HTTPOK: true, Timestamp: now},
	}, now)

	flushOnce(store)

	dayPath := filepath.Join(dir, time.Now().Format("2006/01/02.json"))
	if _, err := os.Stat(dayPath); os.IsNotExist(err) {
		t.Errorf("expected file %s to exist on disk after flushOnce", dayPath)
	}
}

func TestLoadIntoMemoryFromPythonFormat(t *testing.T) {
	dir := setupTempDataDir(t)

	// Python leader writes JSON Lines with node_ip at the top level,
	// same field names (target_ip, ping_ok, http_ok, timestamp).
	// No latency_ms field — Go's omitempty handles the zero value.
	now := float64(time.Now().Unix())
	dayPath := filepath.Join(dir, time.Now().Format("2006/01/02.json"))
	os.MkdirAll(filepath.Dir(dayPath), 0755)
	line := fmt.Sprintf(`{"node_ip":"10.0.0.1","target_ip":"10.0.0.2","ping_ok":true,"http_ok":true,"timestamp":%f}`, now)
	f, err := os.OpenFile(dayPath, os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		t.Fatal(err)
	}
	fmt.Fprintln(f, line)
	f.Close()

	store := NewResultsStore()
	LoadIntoMemory(store)

	raw := store.GetRaw()
	if len(raw) != 1 {
		t.Fatalf("expected 1 node in memory, got %d", len(raw))
	}
	checks := raw["10.0.0.1"]
	if len(checks) != 1 {
		t.Fatalf("expected 1 check for 10.0.0.1, got %d", len(checks))
	}
	if checks[0].TargetIP != "10.0.0.2" {
		t.Errorf("expected target_ip 10.0.0.2, got %s", checks[0].TargetIP)
	}
	if !checks[0].PingOK {
		t.Errorf("expected ping_ok true")
	}
	if !checks[0].HTTPOK {
		t.Errorf("expected http_ok true")
	}
}
