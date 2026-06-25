package leader

import (
	"embed"
	"io/fs"
	"log"
	"net/http"
)

//go:embed staticdist
var staticFiles embed.FS

var staticHandler http.Handler

func init() {
	sub, err := fs.Sub(staticFiles, "staticdist")
	if err != nil {
		log.Printf("Warning: static file server unavailable: %v", err)
		staticHandler = http.NotFoundHandler()
		return
	}
	staticHandler = http.FileServer(http.FS(sub))
}
