package leader

type NodeInfo struct {
	NodeIP     string  `json:"node_ip"`
	Hostname   string  `json:"hostname,omitempty"`
	LastSeen   float64 `json:"last_seen"`
	ListenPort int     `json:"listen_port"`
	NodeURL    string  `json:"node_url,omitempty"`
}

type CheckResult struct {
	TargetIP  string  `json:"target_ip"`
	PingOK    bool    `json:"ping_ok"`
	HTTPOK    bool    `json:"http_ok"`
	Timestamp float64 `json:"timestamp"`
	LatencyMs float64 `json:"latency_ms,omitempty"`
	IsExtra   bool    `json:"is_extra,omitempty"`
}

type RegisterRequest struct {
	NodeIP     string `json:"node_ip"`
	Hostname   string `json:"hostname,omitempty"`
	ListenPort int    `json:"listen_port,omitempty"`
	NodeURL    string `json:"node_url,omitempty"`
}

type SubmitRequest struct {
	NodeIP    string        `json:"node_ip"`
	Checks    []CheckResult `json:"checks"`
	Timestamp *float64      `json:"timestamp,omitempty"`
	NodeURL   string        `json:"node_url,omitempty"`
}

type UpdateConfigRequest struct {
	CheckInterval *int `json:"check_interval,omitempty"`
	BufferSize    *int `json:"buffer_size,omitempty"`
}

type PeerDict struct {
	IP   string `json:"ip"`
	Port int    `json:"port"`
}

type StatusInfo struct {
	SrcIP string `json:"src_ip"`
	DstIP string `json:"dst_ip"`
	Type  string `json:"type"`
	OK    bool   `json:"ok"`
}

type ConnectionStats struct {
	TotalChecks int     `json:"total_checks"`
	PingOK      int     `json:"ping_ok"`
	HTTPOK      int     `json:"http_ok"`
	PingUptime  float64 `json:"ping_uptime_pct"`
	HTTPUptime  float64 `json:"http_uptime_pct"`
}

type DayConnection struct {
	NodeIP      string  `json:"node_ip"`
	TargetIP    string  `json:"target_ip"`
	TotalChecks int     `json:"total_checks"`
	PingOK      int     `json:"ping_ok"`
	HTTPOK      int     `json:"http_ok"`
	PingUptime  float64 `json:"ping_uptime_pct"`
	HTTPUptime  float64 `json:"http_uptime_pct"`
}

type DayEntry struct {
	Date        string          `json:"date"`
	Connections []DayConnection `json:"connections"`
}

type HourEntry struct {
	Date        string          `json:"date"`
	Connections []DayConnection `json:"connections"`
}

var (
	DefaultCheckInterval = 10
	DefaultBufferSize    = 20000
	DefaultListenPort    = 58080
)
