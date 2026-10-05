# Clip waiter for phone notifications (runs on the mini PC, next to Frigate).
# A notification asks for a short video right after an alert starts, before Frigate has saved that part of the
# recording. Instead of failing, this waits (up to 25 s) until the recording covers the requested time, then
# passes Frigate's clip on. So the video shows up as early as it exists, and never comes back empty.
# clip.mp4: the sound is taken out, so the video always plays silently on the phone. clip.gif gives the same seconds
# as a moving picture, which the phone plays by itself as soon as the notification is opened. sound.mp4 keeps the
# sound (for sound alerts, so the right sound can be checked by pressing and holding the notification).
import json, time, re, os, glob, subprocess, tempfile, threading, urllib.request, urllib.parse
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

def stretch(body, want=11.0):
    # Android phones don't play a notification video: they show frames taken from it and need about 10 s of video.
    # For them (?a=1) a short clip is slowed down to ~11 s, so the same seconds the iPhone gets show up as frames
    # right away, instead of waiting for a longer recording.
    try:
        with tempfile.TemporaryDirectory() as d:
            a, b = os.path.join(d, 'in.mp4'), os.path.join(d, 'out.mp4')
            open(a, 'wb').write(body)
            dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', a],
                                       capture_output=True, text=True, timeout=10).stdout.strip() or 0)
            if dur <= 0 or dur >= want:
                return body
            f = want / dur
            subprocess.run(['ffmpeg', '-v', 'error', '-i', a, '-an', '-vf', f'setpts={f:.3f}*PTS', '-r', '10', '-c:v', 'libx264', '-preset', 'veryfast',
                            '-crf', '28', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', b], check=True, timeout=20)
            return open(b, 'rb').read()
    except Exception:
        return body

def silent(body):
    try:
        with tempfile.TemporaryDirectory() as d:
            a, b = os.path.join(d, 'in.mp4'), os.path.join(d, 'out.mp4')
            open(a, 'wb').write(body)
            # small H.264: Android phones (the Samsung) only show a notification video they can decode quickly;
            # the cameras' own HEVC came through as nothing there
            subprocess.run(['ffmpeg', '-v', 'error', '-i', a, '-an', '-vf', "scale='min(640,iw)':-2", '-c:v', 'libx264', '-preset', 'veryfast',
                            '-crf', '27', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', b], check=True, timeout=25)
            return open(b, 'rb').read()
    except Exception:
        return body

def streams(body):
    # which streams a clip has, e.g. "video:hevc audio:pcm_alaw" (no "audio" = the recording has no sound)
    try:
        with tempfile.TemporaryDirectory() as d:
            a = os.path.join(d, 'in.mp4'); open(a, 'wb').write(body)
            out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,codec_name,sample_rate', '-of', 'csv=p=0', a],
                                 capture_output=True, text=True, timeout=10).stdout.split()
            return ' '.join(x.replace(',', ':') for x in out) or 'none'
    except Exception as x:
        return repr(x)

def faststart(body):
    try:
        with tempfile.TemporaryDirectory() as d:
            a, b = os.path.join(d, 'in.mp4'), os.path.join(d, 'out.mp4')
            open(a, 'wb').write(body)
            # sound clips: sound turned into 44.1 kHz stereo AAC. The cameras record 8/16 kHz sound, which the iPhone
            # shows as a video with sound but plays silently (same fix as the app's downloads)
            subprocess.run(['ffmpeg', '-v', 'error', '-i', a, '-map', '0:v:0', '-map', '0:a?', '-vf', "scale='min(640,iw)':-2", '-c:v', 'libx264',
                            '-preset', 'veryfast', '-crf', '27', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-ar', '44100', '-ac', '2', '-b:a', '128k',
                            '-movflags', '+faststart', b], check=True, timeout=25)
            return open(b, 'rb').read()
    except Exception:
        return body

def gif(body, keep=0):
    # keep: only the last `keep` seconds go into the GIF. The clip is asked for with a few seconds before it, so the
    # decoder starts on a full picture; a clip that starts between full pictures (HEVC cameras) otherwise decodes to
    # one frozen frame.
    with tempfile.TemporaryDirectory() as d:
        a, b = os.path.join(d, 'in.mp4'), os.path.join(d, 'out.gif')
        open(a, 'wb').write(body)
        skip = []
        if keep:
            try:
                dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', a],
                                           capture_output=True, text=True, timeout=10).stdout.strip() or 0)
                if dur > keep + 0.5:
                    skip = ['-ss', f'{dur - keep:.2f}']
            except Exception:
                pass
        vf = 'fps=8,scale=480:-2:flags=lanczos,split[x][y];[x]palettegen=stats_mode=diff[p];[y][p]paletteuse=dither=bayer:bayer_scale=4'
        subprocess.run(['ffmpeg', '-v', 'error', '-i', a] + skip + ['-vf', vf, '-loop', '0', b], check=True, timeout=30)
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

def make(path, cam, s, e, kind):
    t0 = time.time()
    ok = False
    # wait for the recording (the phone gives up after ~30 s). Sound clips wait a little longer and never use the
    # live stream: the sound is already in the past, and 9 live seconds on top made the phone give up
    while time.time() - t0 < (25 if kind == 'sound.mp4' else 22):
        if covered(cam, s, e):
            ok = True; break
        time.sleep(0.5)
    # Frigate sometimes can't cut a very short piece right at the edge of a recording segment (some cameras,
    # like Treat Feeder, write longer segments): try the asked seconds, then a slightly wider window once more.
    body, err = None, None
    # Frigate's clip starts on the full picture before the asked second, so it moves from the first frame and is
    # usually a few seconds longer than asked (that is the clip as it always was).
    for a, b, wait in (((s, e, 0), (s - 1, e + 3, 2)) if ok else ()):
        try:
            time.sleep(wait)
            with urllib.request.urlopen(f'{FRIGATE}/api/{cam}/start/{a}/end/{b}/clip.mp4', timeout=30) as r:
                body = r.read()
            if kind == 'sound.mp4':
                print('sound clip from Frigate', cam, a, b, 'streams:', streams(body), flush=True)
            body = gif(body) if kind == 'clip.gif' else faststart(body) if kind == 'sound.mp4' else silent(body)
            if kind == 'sound.mp4':
                print('sound clip sent', cam, 'streams:', streams(body), flush=True)
            break
        except Exception as x:
            err = x; body = None
            print('clip try failed', cam, a, b, kind, repr(x), flush=True)
    if body is None and kind != 'sound.mp4':
        try:
            raw = live(cam, e - s, False)
            body = gif(raw) if kind == 'clip.gif' else raw
            print('clip from live stream', cam, s, e, kind, 'recording ready' if ok else 'recording not ready', flush=True)
        except Exception as x:
            err = x; body = None
            print('live clip failed', cam, kind, repr(x), flush=True)
    if body is not None and kind != 'clip.gif' and 'a=1' in path:
        body = stretch(body)
    return body, err

CACHE, LOCKS, LOCK = {}, {}, threading.Lock()

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
        # The same notification video is asked for more than once (Android reads it in pieces and again when the
        # notification is redrawn): the first request makes it, the others wait for it and get it at once, so a
        # repeat never waits 20 s again and runs past the phone's limit (that made the Samsung video vanish).
        q = urllib.parse.parse_qs(self.path.partition('?')[2])
        andro = q.get('a') == ['1']
        # ?ready=1 is asked by Home Assistant (rest_command.clip_ready) before it sends the notification: the clip is
        # made and kept here, and HA hears "ok" only when it is ready. Then the phone's own request is answered at
        # once, instead of the phone waiting for the recording and giving up ("failed to load attachment").
        ready = q.get('ready') == ['1']
        key = self.path.split('?')[0] + ('?a=1' if andro else '')
        t0 = time.time()
        with LOCK:
            lk = LOCKS.setdefault(key, threading.Lock())
            for k in [k for k, v in CACHE.items() if time.time() - v[1] > 600]:
                CACHE.pop(k, None); LOCKS.pop(k, None) if k != key else None
        with lk:
            hit = CACHE.get(key)
            if hit:
                body, err = hit[0], None
            else:
                body, err = make('?a=1' if andro else '', cam, s, e, kind)
                if body is not None:
                    CACHE[key] = (body, time.time())
        rng = re.match(r'bytes=(\d*)-(\d*)$', self.headers.get('Range', '') or '')
        print('wait', cam, kind, 'a=1' if andro else '', 'ready' if ready else 'phone', 'cached' if hit else 'made',
              f'{time.time() - t0:.1f}s', len(body) if body else 'FAILED', self.headers.get('Range', ''),
              (self.headers.get('User-Agent', '') or '')[:40], flush=True)
        if ready:
            msg = (f'ok {len(body)}' if body else f'failed {err}').encode()
            self.send_response(200 if body else 502)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Content-Length', str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)
            return
        try:
            if body is None:
                raise RuntimeError(err)
            n = len(body)
            if rng and (rng.group(1) or rng.group(2)):
                if rng.group(1):
                    a = int(rng.group(1)); b = min(int(rng.group(2)) if rng.group(2) else n - 1, n - 1)
                else:
                    a = max(0, n - int(rng.group(2))); b = n - 1
                if a >= n:
                    self.send_response(416); self.send_header('Content-Range', f'bytes */{n}'); self.end_headers(); return
                self.send_response(206)
                self.send_header('Content-Range', f'bytes {a}-{b}/{n}')
                part = body[a:b + 1]
            else:
                self.send_response(200)
                part = body
            self.send_header('Content-Type', 'image/gif' if kind == 'clip.gif' else 'video/mp4')
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Content-Length', str(len(part)))
            self.end_headers()
            self.wfile.write(part)
        except Exception:
            try:
                self.send_error(502)
            except Exception:
                pass
    def log_message(self, *a):
        pass

ThreadingHTTPServer(('0.0.0.0', 8000), H).serve_forever()
