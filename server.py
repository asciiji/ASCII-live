"""
ASCII video server: works with curl (terminal) AND in a normal browser (website).
Put <name>.json files next to this file (made by make_frames.py), then:
    python server.py
Terminal:  curl localhost:8000/<name>
Browser:   http://localhost:8000/
"""
import glob, json, os, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CLEAR, HOME = "\033[2J", "\033[H"
GREEN, RESET = "\033[92m", "\033[0m"
HIDE, SHOW = "\033[?25l", "\033[?25h"
MAX_SECONDS = 180

HERE = os.path.dirname(os.path.abspath(__file__))
VIDEOS = {}
for p in glob.glob(os.path.join(HERE, "*.json")) + glob.glob(os.path.join(HERE, "frames", "*.json")):
    with open(p, encoding="utf-8") as f:
        VIDEOS[os.path.basename(p)[:-5].lower()] = json.load(f)

STYLE = """<style>
body{margin:0;background:#0c0c0c;color:#9dff3c;font-family:Consolas,monospace;padding:16px}
a{color:#9dff3c}
h1{font-size:20px;font-weight:normal}
li{margin:10px 0;font-size:18px}
code{background:#1a1a1a;padding:2px 6px;display:inline-block;word-break:break-all}
pre{margin:0;line-height:1}
</style>"""


def gallery(host):
    items = "".join(f'<li><a href="/{n}">&#9654; {n}</a></li>' for n in VIDEOS)
    return f"""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASCII live</title>{STYLE}
<h1>ASCII live</h1><ul>{items}</ul>
<p>Or in a terminal:<br><code>curl https://{host}/{next(iter(VIDEOS), 'name')}</code></p>"""


def player(name):
    return f"""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name}</title>{STYLE}
<p><a href="/">&larr; all videos</a></p>
<pre id="s">Loading...</pre>
<script>
fetch('/{name}.json').then(r=>r.json()).then(d=>{{
  var s=document.getElementById('s'),f=d.frames,i=0;
  var w=f[0].indexOf('\\n');
  var fs=Math.max(4,Math.min(16,(window.innerWidth-32)/(w*0.6)));
  s.style.fontSize=fs+'px';
  function tick(){{s.textContent=f[i%f.length];i++;}}
  tick();setInterval(tick,1000/d.fps);
}});
</script>"""


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _chunk(self, s):
        b = s.encode("utf-8")
        self.wfile.write(f"{len(b):x}\r\n".encode() + b + b"\r\n")
        self.wfile.flush()

    def _send(self, body, ctype):
        b = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        path = self.path.split("?")[0]
        host = self.headers.get("Host", "localhost")
        browser = "mozilla" in self.headers.get("User-Agent", "").lower()

        if path.endswith(".json") and path[1:-5].lower() in VIDEOS:
            return self._send(json.dumps(VIDEOS[path[1:-5].lower()]), "application/json")

        name = path.strip("/").lower()
        if name not in VIDEOS:
            if browser:
                return self._send(gallery(host), "text/html; charset=utf-8")
            lines = "\n".join(f"  curl https://{host}/{n}" for n in VIDEOS)
            return self._send("Run in a terminal:\n\n" + lines + "\n", "text/plain; charset=utf-8")

        if browser:
            return self._send(player(name), "text/html; charset=utf-8")

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
