# Clip waiter for phone notifications (runs on the mini PC, next to Frigate).
# A notification asks for a short video right after an alert starts, before Frigate has saved that part of the
# recording. Instead of failing, this waits (up to 25 s) until the recording covers the requested time, then
# passes Frigate's clip on. So the video shows up as early as it exists, and never comes back empty.
import json, time, re, urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

FRIGATE = 'http://frigate:5000'
PATH = re.compile(r'^/wait/([a-z0-9_]+)/([0-9]+)/([0-9]+)/clip\.mp4$')

def covered(cam, s, e):
    try:
        with urllib.request.urlopen(f'{FRIGATE}/api/{cam}/recordings?after={s - 30}&before={e + 30}', timeout=5) as r:
            rows = json.load(r)
        return any(x['start_time'] <= e and x['end_time'] >= e for x in rows) or any(x['start_time'] > e for x in rows)
    except Exception:
        return False

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        m = PATH.match(self.path.split('?')[0])
        if not m:
            self.send_error(404); return
        cam, s, e = m.group(1), int(m.group(2)), int(m.group(3))
        t0 = time.time()
        while not covered(cam, s, e) and time.time() - t0 < 25:
            time.sleep(0.5)
        try:
            with urllib.request.urlopen(f'{FRIGATE}/api/{cam}/start/{s}/end/{e}/clip.mp4', timeout=30) as r:
                body = r.read()
            self.send_response(200)
            self.send_header('Content-Type', 'video/mp4')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception:
            self.send_error(502)
    def log_message(self, *a):
        pass

ThreadingHTTPServer(('0.0.0.0', 8000), H).serve_forever()
