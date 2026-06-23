package leader

import (
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
