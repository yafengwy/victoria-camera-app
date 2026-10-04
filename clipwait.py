# Clip waiter for phone notifications (runs on the mini PC, next to Frigate).
# A notification asks for a short video right after an alert starts, before Frigate has saved that part of the
# recording. Instead of failing, this waits (up to 25 s) until the recording covers the requested time, then
# passes Frigate's clip on. So the video shows up as early as it exists, and never comes back empty.
# clip.mp4: the sound is taken out, so the video always plays silently on the phone. clip.gif gives the same seconds
# as a moving picture, which the phone plays by itself as soon as the notification is opened. sound.mp4 keeps the
# sound (for sound alerts, so the right sound can be checked by pressing and holding the notification).
import json, time, re, os, subprocess, tempfile, urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

FRIGATE = 'http://frigate:5000'
PATH = re.compile(r'^/wait/([a-z0-9_]+)/([0-9]+)/([0-9]+)/(clip\.mp4|clip\.gif|sound\.mp4)$')

def covered(cam, s, e):
    try:
        with urllib.request.urlopen(f'{FRIGATE}/api/{cam}/recordings?after={s - 30}&before={e + 30}', timeout=5) as r:
            rows = json.load(r)
        return any(x['start_time'] <= e and x['end_time'] >= e for x in rows) or any(x['start_time'] > e for x in rows)
    except Exception:
        return False

def silent(body):
    try:
        with tempfile.TemporaryDirectory() as d:
            a, b = os.path.join(d, 'in.mp4'), os.path.join(d, 'out.mp4')
            open(a, 'wb').write(body)
            subprocess.run(['ffmpeg', '-v', 'error', '-i', a, '-an', '-c:v', 'copy', '-movflags', '+faststart', b], check=True, timeout=20)
            return open(b, 'rb').read()
    except Exception:
        return body

def faststart(body):
    try:
        with tempfile.TemporaryDirectory() as d:
            a, b = os.path.join(d, 'in.mp4'), os.path.join(d, 'out.mp4')
            open(a, 'wb').write(body)
            subprocess.run(['ffmpeg', '-v', 'error', '-i', a, '-c', 'copy', '-movflags', '+faststart', b], check=True, timeout=20)
            return open(b, 'rb').read()
    except Exception:
        return body

def gif(body):
    with tempfile.TemporaryDirectory() as d:
        a, b = os.path.join(d, 'in.mp4'), os.path.join(d, 'out.gif')
        open(a, 'wb').write(body)
        vf = 'fps=8,scale=480:-2:flags=lanczos,split[x][y];[x]palettegen=stats_mode=diff[p];[y][p]paletteuse=dither=bayer:bayer_scale=4'
        subprocess.run(['ffmpeg', '-v', 'error', '-i', a, '-vf', vf, '-loop', '0', b], check=True, timeout=30)
        return open(b, 'rb').read()

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        m = PATH.match(self.path.split('?')[0])
        if not m:
            self.send_error(404); return
        cam, s, e, kind = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
        t0 = time.time()
        while not covered(cam, s, e) and time.time() - t0 < 25:
            time.sleep(0.5)
        try:
            with urllib.request.urlopen(f'{FRIGATE}/api/{cam}/start/{s}/end/{e}/clip.mp4', timeout=30) as r:
                body = r.read()
            body = gif(body) if kind == 'clip.gif' else faststart(body) if kind == 'sound.mp4' else silent(body)
            self.send_response(200)
            self.send_header('Content-Type', 'image/gif' if kind == 'clip.gif' else 'video/mp4')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception:
            self.send_error(502)
    def log_message(self, *a):
        pass

ThreadingHTTPServer(('0.0.0.0', 8000), H).serve_forever()
