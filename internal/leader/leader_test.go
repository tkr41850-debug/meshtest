package leader

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func newTestLeader() *Leader {
	l := NewLeader()
	return l
}

func jsonBody(t *testing.T, v any) *bytes.Buffer {
	t.Helper()
	var buf bytes.Buffer
	if err := json.NewEncoder(&buf).Encode(v); err != nil {
		t.Fatal(err)
	}
	return &buf
}

func decodeJSON(t *testing.T, body *bytes.Buffer, v any) {
	t.Helper()
	if err := json.NewDecoder(body).Decode(v); err != nil {
		t.Fatal(err)
	}
}

func TestLivezReturnsAlive(t *testing.T) {
	l := newTestLeader()
	mux := l.Mux()
	req := httptest.NewRequest("GET", "/livez", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rec.Code)
	}
	var resp map[string]string
	decodeJSON(t, rec.Body, &resp)
	if resp["status"] != "alive" {
		t.Errorf("expected alive, got %s", resp["status"])
	}
}

func TestReadyzReturnsReady(t *testing.T) {
	l := newTestLeader()
	mux := l.Mux()
	req := httptest.NewRequest("GET", "/readyz", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rec.Code)
	}
	var resp map[string]string
	decodeJSON(t, rec.Body, &resp)
	if resp["status"] != "ready" {
		t.Errorf("expected ready, got %s", resp["status"])
	}
}

func TestHealthzReturnsAlive(t *testing.T) {
	l := newTestLeader()
	mux := l.Mux()
	req := httptest.NewRequest("GET", "/healthz", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rec.Code)
	}
	var resp map[string]string
	decodeJSON(t, rec.Body, &resp)
	if resp["status"] != "alive" {
		t.Errorf("expected alive, got %s", resp["status"])
	}
}

func TestRegisterNodeReturnsPeers(t *testing.T) {
	l := newTestLeader()
	mux := l.Mux()

	req := httptest.NewRequest("POST", "/register", jsonBody(t, map[string]string{"node_ip": "10.0.0.1"}))
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rec.Code)
	}
	var resp map[string]any
	decodeJSON(t, rec.Body, &resp)
	if resp["status"] != "registered" {
		t.Errorf("expected registered, got %s", resp["status"])
	}
	if _, ok := resp["peers"]; !ok {
		t.Error("expected peers key in response")
	}
}

func TestRegisterDuplicateIsIdempotent(t *testing.T) {
	l := newTestLeader()
	mux := l.Mux()

	for i := 0; i < 2; i++ {
		req := httptest.NewRequest("POST", "/register", jsonBody(t, map[string]string{"node_ip": "10.0.0.1"}))
		rec := httptest.NewRecorder()
		mux.ServeHTTP(rec, req)
		if rec.Code != http.StatusOK {
			t.Errorf("attempt %d: expected 200, got %d", i+1, rec.Code)
		}
	}
}

func TestRegisterMissingIPReturns400(t *testing.T) {
	l := newTestLeader()
	mux := l.Mux()

	req := httptest.NewRequest("POST", "/register", jsonBody(t, map[string]any{}))
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", rec.Code)
	}
}

func TestRegisterMissingBodyReturns400(t *testing.T) {
	l := newTestLeader()
	mux := l.Mux()

	req := httptest.NewRequest("POST", "/register", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", rec.Code)
	}
}

func TestNodeListReturnsRegisteredNodes(t *testing.T) {
	l := newTestLeader()
	mux := l.Mux()

	mux.ServeHTTP(httptest.NewRecorder(),
		httptest.NewRequest("POST", "/register", jsonBody(t, map[string]string{"node_ip": "10.0.0.1"})))
	mux.ServeHTTP(httptest.NewRecorder(),
		httptest.NewRequest("POST", "/register", jsonBody(t, map[string]string{"node_ip": "10.0.0.2"})))

	req := httptest.NewRequest("GET", "/node-list", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rec.Code)
	}
	var resp map[string]any
	decodeJSON(t, rec.Body, &resp)
	if count := resp["count"].(float64); count != 2 {
		t.Errorf("expected count 2, got %f", count)
	}
}

func TestNodeListEmptyInitially(t *testing.T) {
	l := newTestLeader()
	mux := l.Mux()

	req := httptest.NewRequest("GET", "/node-list", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	var resp map[string]any
	decodeJSON(t, rec.Body, &resp)
	if count := resp["count"].(float64); count != 0 {
		t.Errorf("expected count 0, got %f", count)
	}
}

func TestSubmitChecksReturnsAccepted(t *testing.T) {
	l := newTestLeader()
	mux := l.Mux()

	ts := float64(time.Now().Unix())
	payload := SubmitRequest{
		NodeIP: "10.0.0.1",
		Checks: []CheckResult{
			{TargetIP: "10.0.0.2", PingOK: true, HTTPOK: true, Timestamp: float64(time.Now().Unix())},
		},
		Timestamp: &ts,
	}
	req := httptest.NewRequest("POST", "/submit", jsonBody(t, payload))
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusAccepted {
		t.Errorf("expected 202, got %d", rec.Code)
	}
	var resp map[string]any
	decodeJSON(t, rec.Body, &resp)
	if resp["status"] != "accepted" {
		t.Errorf("expected accepted, got %s", resp["status"])
	}
}

func TestSubmitEmptyBodyReturns400(t *testing.T) {
	l := newTestLeader()
	mux := l.Mux()

	req := httptest.NewRequest("POST", "/submit", jsonBody(t, map[string]any{}))
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", rec.Code)
	}
}

func TestSubmitMissingNodeIPReturns400(t *testing.T) {
	l := newTestLeader()
	mux := l.Mux()

	payload := map[string]any{
		"checks":    []CheckResult{},
		"timestamp": float64(time.Now().Unix()),
	}
	req := httptest.NewRequest("POST", "/submit", jsonBody(t, payload))
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", rec.Code)
	}
}

func TestSubmitEmptyChecksReturns400(t *testing.T) {
	l := newTestLeader()
	mux := l.Mux()

	payload := map[string]any{
		"node_ip":   "10.0.0.1",
		"checks":    []CheckResult{},
		"timestamp": float64(time.Now().Unix()),
	}
	req := httptest.NewRequest("POST", "/submit", jsonBody(t, payload))
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", rec.Code)
	}
}

func TestSubmitMissingTimestampReturns400(t *testing.T) {
	l := newTestLeader()
	mux := l.Mux()

	payload := map[string]any{
		"node_ip": "10.0.0.1",
		"checks": []map[string]any{
			{"target_ip": "10.0.0.2", "ping_ok": true, "http_ok": true},
		},
	}
	req := httptest.NewRequest("POST", "/submit", jsonBody(t, payload))
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", rec.Code)
	}
}

func TestData90mReturnsChecksAndStatuses(t *testing.T) {
	l := newTestLeader()
	mux := l.Mux()
	now := float64(time.Now().Unix())

	mux.ServeHTTP(httptest.NewRecorder(),
		httptest.NewRequest("POST", "/register", jsonBody(t, map[string]string{"node_ip": "10.0.0.1"})))
	mux.ServeHTTP(httptest.NewRecorder(),
		httptest.NewRequest("POST", "/register", jsonBody(t, map[string]string{"node_ip": "10.0.0.2"})))
	mux.ServeHTTP(httptest.NewRecorder(),
		httptest.NewRequest("POST", "/submit", jsonBody(t, SubmitRequest{
			NodeIP: "10.0.0.1",
			Checks: []CheckResult{
				{TargetIP: "10.0.0.2", PingOK: true, HTTPOK: true, Timestamp: now},
			},
			Timestamp: &now,
		})))

	req := httptest.NewRequest("GET", "/data?window=90m", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rec.Code)
	}
	var resp QueryResult90m
	decodeJSON(t, rec.Body, &resp)
	if resp.Window != "90m" {
		t.Errorf("expected window 90m, got %s", resp.Window)
	}
	if len(resp.Checks) == 0 {
		t.Error("expected non-empty checks")
	}
	if len(resp.Statuses) == 0 {
		t.Error("expected non-empty statuses")
	}
}

func TestData90hReturnsHours(t *testing.T) {
	l := newTestLeader()
	mux := l.Mux()
	now := float64(time.Now().Unix())

	mux.ServeHTTP(httptest.NewRecorder(),
		httptest.NewRequest("POST", "/submit", jsonBody(t, SubmitRequest{
			NodeIP: "10.0.0.1",
			Checks: []CheckResult{
				{TargetIP: "10.0.0.2", PingOK: true, HTTPOK: true, Timestamp: now},
			},
			Timestamp: &now,
		})))

	req := httptest.NewRequest("GET", "/data?window=90h", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rec.Code)
	}
	var resp QueryResult90h
	decodeJSON(t, rec.Body, &resp)
	if resp.Window != "90h" {
		t.Errorf("expected window 90h, got %s", resp.Window)
	}
	if len(resp.Hours) == 0 {
		t.Error("expected non-empty hours")
	}
}

func TestData90dReturnsDays(t *testing.T) {
	l := newTestLeader()
	mux := l.Mux()
	now := float64(time.Now().Unix())

	mux.ServeHTTP(httptest.NewRecorder(),
		httptest.NewRequest("POST", "/submit", jsonBody(t, SubmitRequest{
			NodeIP: "10.0.0.1",
			Checks: []CheckResult{
				{TargetIP: "10.0.0.2", PingOK: true, HTTPOK: true, Timestamp: now},
			},
			Timestamp: &now,
		})))

	req := httptest.NewRequest("GET", "/data?window=90d", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rec.Code)
	}
	var resp QueryResult90d
	decodeJSON(t, rec.Body, &resp)
	if resp.Window != "90d" {
		t.Errorf("expected window 90d, got %s", resp.Window)
	}
	if len(resp.Days) == 0 {
		t.Error("expected non-empty days")
	}
}

func TestDataInvalidWindowReturns400(t *testing.T) {
	l := newTestLeader()
	mux := l.Mux()

	req := httptest.NewRequest("GET", "/data?window=invalid", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", rec.Code)
	}
}

func TestDataMissingWindowReturns400(t *testing.T) {
	l := newTestLeader()
	mux := l.Mux()

	req := httptest.NewRequest("GET", "/data", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", rec.Code)
	}
}

func TestUpdateConfigAcceptsValidValues(t *testing.T) {
	l := newTestLeader()
	mux := l.Mux()

	ci := 30
	bs := 5000
	req := httptest.NewRequest("POST", "/updateConfig", jsonBody(t, UpdateConfigRequest{
		CheckInterval: &ci,
		BufferSize:    &bs,
	}))
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rec.Code)
	}
	var resp map[string]any
	decodeJSON(t, rec.Body, &resp)
	if resp["status"] != "config_updated" {
		t.Errorf("expected config_updated, got %s", resp["status"])
	}
}

func TestUpdateConfigEmptyBodyReturns400(t *testing.T) {
	l := newTestLeader()
	mux := l.Mux()

	req := httptest.NewRequest("POST", "/updateConfig", jsonBody(t, map[string]any{}))
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", rec.Code)
	}
}

func TestUpdateConfigNegativeIntervalReturns400(t *testing.T) {
	l := newTestLeader()
	mux := l.Mux()

	ci := -1
	req := httptest.NewRequest("POST", "/updateConfig", jsonBody(t, UpdateConfigRequest{
		CheckInterval: &ci,
	}))
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", rec.Code)
	}
}

func TestRegistryIsThreadSafe(t *testing.T) {
	l := newTestLeader()
	done := make(chan bool)
	for i := 0; i < 100; i++ {
		go func(n int) {
			ip := formatIP(n)
			l.Registry.Register(RegisterRequest{NodeIP: ip})
			l.Registry.All()
			l.Registry.PeerDicts()
			done <- true
		}(i)
	}
	for i := 0; i < 100; i++ {
		<-done
	}
	nodes := l.Registry.All()
	if len(nodes) != 100 {
		t.Errorf("expected 100 nodes, got %d", len(nodes))
	}
}

func TestResultsStoreIsThreadSafe(t *testing.T) {
	l := newTestLeader()
	done := make(chan bool)
	for i := 0; i < 100; i++ {
		go func() {
			l.Results.Add("10.0.0.1", []CheckResult{
				{TargetIP: "10.0.0.2", PingOK: true, HTTPOK: true, Timestamp: float64(time.Now().Unix())},
			}, float64(time.Now().Unix()))
			l.Results.GetRaw()
			done <- true
		}()
	}
	for i := 0; i < 100; i++ {
		<-done
	}
	raw := l.Results.GetRaw()
	if len(raw) != 1 {
		t.Errorf("expected 1 node in results, got %d", len(raw))
	}
}

func formatIP(n int) string {
	return fmt.Sprintf("10.0.0.%d", n%255+1)
}

func TestSubmitAutoRegistersNode(t *testing.T) {
	l := newTestLeader()
	mux := l.Mux()
	now := float64(time.Now().Unix())

	mux.ServeHTTP(httptest.NewRecorder(),
		httptest.NewRequest("POST", "/submit", jsonBody(t, SubmitRequest{
			NodeIP: "10.0.0.1",
			Checks: []CheckResult{
				{TargetIP: "10.0.0.2", PingOK: true, HTTPOK: true, Timestamp: now},
			},
			Timestamp: &now,
			NodeURL:   "http://10.0.0.1:58080",
		})))

	if l.Registry.Get("10.0.0.1") == nil {
		t.Error("expected node to be auto-registered from submit")
	}
}

func TestExtraTargetExcludedFromStatuses(t *testing.T) {
	l := newTestLeader()
	mux := l.Mux()
	now := float64(time.Now().Unix())

	mux.ServeHTTP(httptest.NewRecorder(),
		httptest.NewRequest("POST", "/register", jsonBody(t, map[string]string{"node_ip": "10.0.0.1"})))
	mux.ServeHTTP(httptest.NewRecorder(),
		httptest.NewRequest("POST", "/register", jsonBody(t, map[string]string{"node_ip": "10.0.0.2"})))

	// Submit both a normal check (failed) and an extra check (passed) from 10.0.0.1→10.0.0.2
	mux.ServeHTTP(httptest.NewRecorder(),
		httptest.NewRequest("POST", "/submit", jsonBody(t, SubmitRequest{
			NodeIP: "10.0.0.1",
			Checks: []CheckResult{
				{TargetIP: "10.0.0.2", PingOK: false, HTTPOK: false, Timestamp: now, IsExtra: false},
				{TargetIP: "10.0.0.2", PingOK: true, HTTPOK: true, Timestamp: now, IsExtra: true},
			},
			Timestamp: &now,
		})))

	req := httptest.NewRequest("GET", "/data?window=90m", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rec.Code)
	}
	var resp QueryResult90m
	decodeJSON(t, rec.Body, &resp)

	// Both checks should appear in the checks array with correct IsExtra values
	normalFound := false
	extraFound := false
	for _, c := range resp.Checks {
		if c.TargetIP == "10.0.0.2" && c.NodeIP == "10.0.0.1" && !c.IsExtra {
			normalFound = true
			if c.PingOK || c.HTTPOK {
				t.Error("normal check should have false PingOK/HTTPOK")
			}
		}
		if c.TargetIP == "10.0.0.2" && c.NodeIP == "10.0.0.1" && c.IsExtra {
			extraFound = true
			if !c.PingOK || !c.HTTPOK {
				t.Error("extra check should have true PingOK/HTTPOK")
			}
		}
	}
	if !normalFound {
		t.Error("expected normal check in checks array")
	}
	if !extraFound {
		t.Error("expected extra check in checks array with IsExtra=true")
	}

	// checkPairStatus should skip the IsExtra check.
	// The normal check has PingOK=false, HTTPOK=false, so status should be false.
	for _, st := range resp.Statuses {
		if st.SrcIP == "10.0.0.1" && st.DstIP == "10.0.0.2" && st.OK {
			t.Errorf("expected false status for 10.0.0.1→10.0.0.2 (skipped IsExtra check, normal check is false); got type=%s ok=true", st.Type)
		}
	}
}

func TestCORSHeaders(t *testing.T) {
	l := newTestLeader()
	mux := l.Mux()

	req := httptest.NewRequest("GET", "/livez", nil)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, req)

	if rec.Header().Get("Access-Control-Allow-Origin") != "*" {
		t.Error("expected CORS header")
	}
}
