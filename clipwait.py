# Clip waiter for phone notifications (runs on the mini PC, next to Frigate).
# A notification asks for a short video right after an alert starts, before Frigate has saved that part of the
# recording. Instead of failing, this waits (up to 25 s) until the recording covers the requested time, then
# passes Frigate's clip on. So the video shows up as early as it exists, and never comes back empty.
# clip.mp4: the sound is taken out, so the video always plays silently on the phone. clip.gif gives the same seconds
# as a moving picture, which the phone plays by itself as soon as the notification is opened. sound.mp4 keeps the
# sound (for sound alerts, so the right sound can be checked by pressing and holding the notification).
import json, time, re, os, glob, subprocess, tempfile, urllib.request
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

FRIGATE = 'http://frigate:5000'
PATH = re.compile(r'^/wait/([a-z0-9_]+)/([0-9]+)/([0-9]+)/(clip\.mp4|clip\.gif|sound\.mp4)$')
# Downloads from the app: the same seconds with the date and time burned into the top-left corner.
# /stamp/<camera>/<start>/<end>/<utc offset in seconds>/clip.mp4
STAMP = re.compile(r'^/stamp/([a-z0-9_]+)/([0-9]+)/([0-9]+)/(-?[0-9]+)/clip\.mp4$')

def covered(cam, s, e):
    try:
        with urllib.request.urlopen(f'{FRIGATE}/api/{cam}/recordings?after={s - 30}&before={e + 30}', timeout=5) as r:
            rows = json.load(r)
        return any(x['start_time'] <= e and x['end_time'] >= e for x in rows) or any(x['start_time'] > e for x in rows)
    except Exception:
        return False

def live(cam, secs, audio):
    # Recordings of some cameras (Treat Feeder, Living Room) reach Frigate's storage late, so a clip asked for right
    # after the alert isn't there yet. Then take the next few seconds straight from the camera's live stream instead
    # (go2rtc inside the Frigate container), so the phone still gets a moving picture within seconds.
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, 'live.mp4')
        subprocess.run(['ffmpeg', '-v', 'error', '-rtsp_transport', 'tcp', '-i', f'rtsp://frigate:8554/{cam}', '-t', str(max(2, secs)),
                        '-map', '0:v:0'] + (['-map', '0:a?', '-c:a', 'aac'] if audio else ['-an']) + ['-c:v', 'copy', '-movflags', '+faststart', '-y', out],
                       check=True, timeout=max(2, secs) + 15)
        return open(out, 'rb').read()

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

def font():
    f = glob.glob('/usr/share/fonts/**/DejaVuSans.ttf', recursive=True)
    if not f:
        subprocess.run(['apk', 'add', '--no-cache', 'font-dejavu'], capture_output=True, timeout=120)
        f = glob.glob('/usr/share/fonts/**/DejaVuSans.ttf', recursive=True)
    return f[0] if f else None

def stamp_vf(base, w=1920):
    # w=0: keep the camera's own size (computer downloads)
    fmt = '%Y/%m/%d %H\\\\\\:%M\\\\\\:%S'
    ff = font()
    return ((f"scale='min({w},iw)':-2," if w else '') + "drawtext=" + (f'fontfile={ff}:' if ff else '') +
            "text='%{pts\\:gmtime\\:" + str(base) + "\\:" + fmt + "}':x=16:y=16:fontsize=h/24:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=8")

def encode(args, vf, out, full=False):
    # phone: H.264 High 4.1 the iPhone's Photos accepts; computer (full): the camera's own size at near-original quality
    q = ['-crf', '17'] if full else ['-crf', '23', '-level:v', '4.1']
    subprocess.run(['ffmpeg', '-v', 'error'] + args + ['-map', '0:v:0', '-map', '0:a?', '-vf', vf, '-c:v', 'libx264', '-preset', 'veryfast'] + q +
                   ['-pix_fmt', 'yuv420p', '-profile:v', 'high', '-tag:v', 'avc1',
                    '-c:a', 'aac', '-ar', '44100', '-movflags', '+faststart', '-y', out], check=True, timeout=900)

def stamped(cam, s, e, off, full=False):
    w = 0 if full else (1920 if e - s <= 120 else 1280)
    # The recording pieces themselves (each piece's start time is known exactly), joined and cut on the exact second,
    # so the burned-in clock matches the picture. Frigate's clip.mp4 starts on the key frame before the asked second.
    with tempfile.TemporaryDirectory() as d:
        try:
            with urllib.request.urlopen(f'{FRIGATE}/api/{cam}/recordings?after={s - 60}&before={e + 1}', timeout=10) as r:
                rows = sorted((x for x in json.load(r) if x['end_time'] > s and x['start_time'] < e), key=lambda x: x['start_time'])
            files = []
            for i, x in enumerate(rows):
                st, got = int(x['start_time']), None
                for t in (st, st - 1, st + 1):
                    dt = datetime.fromtimestamp(t, timezone.utc)
                    try:
                        with urllib.request.urlopen(f'{FRIGATE}/recordings/{dt:%Y-%m-%d}/{dt:%H}/{cam}/{dt:%M.%S}.mp4', timeout=30) as r:
                            got = r.read(); break
                    except Exception:
                        pass
                if got is None:
                    raise RuntimeError('missing piece')
                fn = os.path.join(d, f'{i:04d}.mp4'); open(fn, 'wb').write(got); files.append(fn)
            if not files:
                raise RuntimeError('no pieces')
            lst = os.path.join(d, 'list.txt')
            open(lst, 'w').write(''.join(f"file '{f}'\n" for f in files))
            out = os.path.join(d, 'out.mp4')
            encode(['-f', 'concat', '-safe', '0', '-ss', str(max(0, s - rows[0]['start_time'])), '-i', lst, '-t', str(e - s)], stamp_vf(s + off, w), out, full)
            return open(out, 'rb').read()
        except Exception as x:
            print('stamp from pieces failed, using the clip:', cam, s, e, x)
        a, out = os.path.join(d, 'in.mp4'), os.path.join(d, 'out2.mp4')
        with urllib.request.urlopen(f'{FRIGATE}/api/{cam}/start/{s}/end/{e}/clip.mp4', timeout=60) as r:
            open(a, 'wb').write(r.read())
        encode(['-i', a], stamp_vf(s + off, w), out, full)
        return open(out, 'rb').read()

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        st = STAMP.match(self.path.split('?')[0])
        if st:
            try:
                body = stamped(st.group(1), int(st.group(2)), int(st.group(3)), int(st.group(4)), 'full=1' in self.path)
                self.send_response(200)
                self.send_header('Content-Type', 'video/mp4')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as x:
                print('stamp failed', self.path, x)
                self.send_error(502)
            return
        m = PATH.match(self.path.split('?')[0])
        if not m:
            self.send_error(404); return
        cam, s, e, kind = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
        t0 = time.time()
        ok = False
        while time.time() - t0 < 8:   # the phone gives up after ~30 s, so don't wait long for the recording
            if covered(cam, s, e):
                ok = True; break
            time.sleep(0.5)
        # Frigate sometimes can't cut a very short piece right at the edge of a recording segment (some cameras,
        # like Treat Feeder, write longer segments): try the asked seconds, then a slightly wider window once more.
        body, err = None, None
        for a, b, wait in (((s, e, 0), (s - 1, e + 3, 2)) if ok else ()):
            try:
                time.sleep(wait)
                with urllib.request.urlopen(f'{FRIGATE}/api/{cam}/start/{a}/end/{b}/clip.mp4', timeout=30) as r:
                    body = r.read()
                body = gif(body) if kind == 'clip.gif' else faststart(body) if kind == 'sound.mp4' else silent(body)
                break
            except Exception as x:
                err = x; body = None
                print('clip try failed', cam, a, b, kind, repr(x), flush=True)
        if body is None:
            try:
                raw = live(cam, e - s, kind == 'sound.mp4')
                body = gif(raw) if kind == 'clip.gif' else raw
                print('clip from live stream', cam, s, e, kind, 'recording ready' if ok else 'recording not ready', flush=True)
            except Exception as x:
                err = x; body = None
                print('live clip failed', cam, kind, repr(x), flush=True)
        try:
            if body is None:
                raise RuntimeError(err)
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
