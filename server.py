"""
Streams ASCII videos to the terminal, like ascii.live.
Put frames in frames/<name>.json (made by make_frames.py), then:
    python server.py
    curl localhost:8000/<name>
"""
import glob, json, os, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CLEAR, HOME = "\033[2J", "\033[H"
GREEN, RESET = "\033[92m", "\033[0m"
HIDE, SHOW = "\033[?25l", "\033[?25h"
MAX_SECONDS = 180

VIDEOS = {}
HERE = os.path.dirname(os.path.abspath(__file__))
for p in glob.glob(os.path.join(HERE, "*.json")) + glob.glob(os.path.join(HERE, "frames", "*.json")):
    with open(p, encoding="utf-8") as f:
        VIDEOS[os.path.basename(p)[:-5].lower()] = json.load(f)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _chunk(self, s):
        b = s.encode("utf-8")
        self.wfile.write(f"{len(b):x}\r\n".encode() + b + b"\r\n")
        self.wfile.flush()

    def _plain(self, text):
        b = text.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        name = self.path.split("?")[0].strip("/").lower()
        host = self.headers.get("Host", "localhost")
        if name not in VIDEOS or "mozilla" in self.headers.get("User-Agent", "").lower():
            lines = "\n".join(f"  curl {host}/{n}" for n in VIDEOS)
            return self._plain("Run in a terminal:\n\n" + lines + "\n")

        v = VIDEOS[name]
        delay = 1.0 / v["fps"]
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Transfer-Encoding", "chunked")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        try:
            self._chunk(HIDE + CLEAR)
            end = time.time() + MAX_SECONDS
            while time.time() < end:
                for fr in v["frames"]:
                    self._chunk(HOME + GREEN + fr + RESET)
                    time.sleep(delay)
            self._chunk(SHOW + "\n")
            self.wfile.write(b"0\r\n\r\n")
        except (BrokenPipeError, ConnectionResetError):
            pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Loaded videos: {list(VIDEOS)}  | port {port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
