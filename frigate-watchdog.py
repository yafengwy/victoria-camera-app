#!/usr/bin/env python3
# Frigate watchdog (runs every minute from update-app.sh on the mini PC).
# 2026-10-04 night: Frigate's graphics-card decoding failed ("Failed to sync surface", "hardware accelerator failed")
# around 23:00 and stayed broken until a manual `docker restart frigate` at 08:40 the next morning: no live pictures,
# no detection, recordings discarded. This restarts Frigate by itself when that happens:
#   - 5 or more enabled cameras give no frames (camera_fps < 1) for 5 checks in a row, or
#   - 60+ graphics decode errors in the last 2 minutes for 5 checks in a row (normal is ~10), or
#   - Frigate's API does not answer for 5 checks in a row.
# Never within 10 minutes of Frigate starting, and at most once every 30 minutes. Each restart is logged with the
# cameras that were stuck, in ~/frigate/watchdog-log.txt, so the cause can be read afterwards.
import calendar, json, os, re, shutil, subprocess, time, urllib.request
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo('America/Los_Angeles')
except Exception:
    TZ = None

D = os.path.expanduser('~/frigate')
STATE = os.path.join(D, '.watchdog.json')
LOG = os.path.join(D, 'watchdog-log.txt')
API = 'http://127.0.0.1:5000/api'
# Camera down alerts: a camera Frigate keeps trying (and failing) to read, with no picture for 10 minutes, sends one
# phone notification through Home Assistant (automation "Camera No Picture", webhook trigger, local network only);
# again at most every 3 hours while it stays down. Cameras switched off on purpose give no Frigate log lines, so they
# never count. 2026-10-05: Closet had broken pictures for over an hour (Wi-Fi) and nobody knew.
HOOK = 'http://192.168.1.252:8123/api/webhook/vh-camera-down-6a53d96d5efbd590'
DOWN_MIN, DOWN_EVERY = 600, 3 * 3600
QUIET = {'nest_master_bedroom'}
# Daily fresh start at 4:00 California time (her choice): the Furbo and Xiaomi bridges, then Frigate, so stuck camera
# sessions and decoders start clean once a day. All cameras pause about 2 minutes.
DAILY_HOUR = 4   # turned off in Google Home on purpose; take it out of here when it is back on
# Furbo bridge stuck (her choice, 2026-10-05): Upstairs Furbo stalled with the bridge answering 409 (stream_busy, "a
# viewer is already streaming") and timeouts while the camera itself was fine on the network. When a Furbo camera has
# no picture, Frigate keeps trying, and the furbo container's log shows those errors, for 10 checks in a row, restart
# only the furbo container (all 4 Furbo cameras pause ~1 min; Frigate reconnects by itself). At most once an hour and
# 3 times a day, because each restart logs in to the Furbo cloud again.
FURBO_ERR = ('409', 'stream_busy', 'already streaming', 'p2p_unavailable', 'timed out', 'timeout')
FURBO_RUNS, FURBO_GAP, FURBO_DAY = 10, 3600, 3
# Storage alert (her choice, 2026-10-07, idea from Camect): every 6 hours, how many days back the kept alerts reach and
# how full the recordings disk is. One phone notification a day (automation "Camera Storage", webhook, local network
# only) when alerts reach back fewer than 25 days (only once the system is older than that) or the disk has < 10% free.
STORE_HOOK = 'http://192.168.1.252:8123/api/webhook/vh-camera-storage-865b860917997d36'
STORE_DAYS, STORE_FREE, STORE_EVERY = 25, 0.10, 6 * 3600
# Furbo 360s to the Furbo app (her choice, 2026-10-08): the bridge holds a session to every Furbo all the time, and a
# Furbo takes one session only, so the Furbo app could not reach Upstairs / Bedroom. A button in the app's Settings
# (served by clipwait, written to ~/frigate/furbo-ctl/want) hands those two to the Furbo app: the bridge then serves
# only the two bowls (device_id in furbo-data/options.json) and is restarted; the button again gives them back.
# While handed over, those two cameras never count as down and never restart the bridge.
# Xiaomi bridge stuck (her choice, 2026-10-09): 猫砂盆 (litter_box, the only camera on the xiaomi go2rtc) had no
# picture and came back only by itself or by restarting the xiaomi container. When it has no picture and Frigate keeps
# trying for 10 checks in a row (10 min), restart only the xiaomi container (猫砂盆 pauses ~30 s). At most once an hour
# and 3 times a day; logged in Mini PC Log → Automatic Restarts.
XIAOMI_CAMS = {'litter_box'}
XIAOMI_RUNS, XIAOMI_GAP, XIAOMI_DAY = 10, 3600, 3
CTL = os.path.join(D, 'furbo-ctl', 'want')
FURBO_BOWLS = '507B91E283B6,D07CB28A9D20'          # 胖胖饭桶, 团团饭桶
FURBO_360 = {'upstairs_furbo', 'bedroom_furbo'}


def get(path):
    with urllib.request.urlopen(API + path, timeout=8) as r:
        return json.load(r)


def log(msg):
    line = time.strftime('%m-%d %H:%M ') + msg
    with open(LOG, 'a') as f:
        f.write(line + '\n')
    try:  # keep the log small
        if os.path.getsize(LOG) > 50000:
            data = open(LOG).read()[-25000:]
            open(LOG, 'w').write(data)
    except OSError:
        pass


def started_ago():
    try:
        s = subprocess.run(['docker', 'inspect', '-f', '{{.State.StartedAt}}', 'frigate'], capture_output=True, text=True, timeout=10).stdout.strip()
        t = calendar.timegm(time.strptime(s[:19], '%Y-%m-%dT%H:%M:%S'))   # Docker gives UTC
        return time.time() - t
    except Exception:
        return 1e9


def gpu_errors():
    try:
        out = subprocess.run(['docker', 'logs', 'frigate', '--since', '2m'], capture_output=True, text=True, timeout=20)
        txt = out.stdout + out.stderr
        return sum(txt.count(k) for k in ('Failed to sync surface', 'hardware accelerator failed', 'Failed to download frame'))
    except Exception:
        return 0


def sh(args, t=20):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=t); return r.stdout + r.stderr
    except Exception:
        return ''


DEC = ('Failed to sync surface', 'hardware accelerator failed', 'Failed to download frame', 'Missing reference')


def counts(txt):
    # per camera: graphics decode errors, ffmpeg crashes, recordings discarded (Frigate could not keep up)
    c = {'dec': {}, 'crash': {}, 'disc': {}}
    for line in txt.splitlines():
        cam = None
        if any(k in line for k in DEC):
            m = re.search(r'ffmpeg\.([a-z0-9_]+)\.', line); k = 'dec'; cam = m and m.group(1)
        elif 'Ffmpeg process crashed unexpectedly for' in line:
            m = re.search(r'unexpectedly for ([a-z0-9_]+)', line); k = 'crash'; cam = m and m.group(1)
        elif 'Unable to keep up with recording segments' in line:
            m = re.search(r'cache for ([a-z0-9_]+)', line); k = 'disc'; cam = m and m.group(1)
        if cam:
            c[k][cam] = c[k].get(cam, 0) + 1
    return c


def top(d, n=4):
    return ', '.join('%s %d' % kv for kv in sorted(d.items(), key=lambda x: -x[1])[:n]) if d else 'None'


def furbo_want():
    try:
        return open(CTL).read().strip()
    except OSError:
        return 'app'


def released():
    return FURBO_360 if furbo_want() == 'furbo' else set()


def furbo360():
    # makes the bridge's device_id match the Settings button; writes app/furbo360.txt for the app to show
    want = furbo_want(); dev = FURBO_BOWLS if want == 'furbo' else ''
    try:
        o = json.load(open(os.path.join(D, 'furbo-data', 'options.json')))
    except Exception:
        return
    cur = (o.get('device_id') or '').strip()
    if cur != dev:
        o['device_id'] = dev
        tmp = os.path.join(D, '.furbo-options.tmp')
        try:
            json.dump(o, open(tmp, 'w'), indent=2); os.chmod(tmp, 0o600)
            r = subprocess.run(['docker', 'cp', tmp, 'furbo:/data/options.json'], capture_output=True, text=True, timeout=60)
            if r.returncode != 0:
                log('furbo 360 switch failed: ' + (r.stderr or '').strip()[:150]); return
            subprocess.run(['docker', 'restart', 'furbo'], capture_output=True, text=True, timeout=120)
            log('furbo 360s given to the Furbo app (bridge serves the two bowls only)' if dev else 'furbo 360s back in the camera app (bridge serves all 4)')
            cur = dev
        finally:
            try: os.remove(tmp)
            except OSError: pass
    try:
        tmp = os.path.join(D, 'app', 'furbo360.txt.tmp'); open(tmp, 'w').write(json.dumps({'want': want, 'now': 'furbo' if cur else 'app'})); os.replace(tmp, os.path.join(D, 'app', 'furbo360.txt'))
    except Exception:
        pass


def down_alerts(dead, st, t10):
    # returns lines for the Mini PC Log: cameras down now (since when) and the last alerts sent
    now = time.time(); dn = st.setdefault('down', {}); sent = st.setdefault('down_sent', {}); hist = st.setdefault('down_log', [])
    tz = lambda t, f='%H:%M': (datetime.fromtimestamp(t, TZ) if TZ else datetime.fromtimestamp(t)).strftime(f)
    trying = {c for c in dead if ('watchdog.%s ' % c) in t10 or ('ffmpeg.%s.' % c) in t10 or (': %s:' % c) in t10}
    for c in list(dn):
        if c not in trying:
            if sent.get(c, 0) > dn[c]:
                hist.append(tz(now, '%m-%d %H:%M ') + c + ' picture back')
            del dn[c]
    rel = released()
    for c in list(dn):
        if c in rel: del dn[c]
    for c in trying:
        if c in QUIET or c in rel:
            continue
        dn.setdefault(c, now)
        mins = int((now - dn[c]) // 60)
        if now - dn[c] >= DOWN_MIN and now - sent.get(c, 0) >= DOWN_EVERY:
            name = (st.get('names') or {}).get(c, c)
            ok = 'sent'
            try:
                req = urllib.request.Request(HOOK, data=json.dumps({'cam': c, 'name': name, 'minutes': mins}).encode(), headers={'Content-Type': 'application/json'}, method='POST')
                urllib.request.urlopen(req, timeout=8).read()
            except Exception as x:
                ok = 'not sent (' + repr(x)[:80] + ')'
            sent[c] = now
            hist.append(tz(now, '%m-%d %H:%M ') + '%s no picture %d min · alert %s' % (c, mins, ok))
    del hist[:-10]
    cur = ['Down Now: ' + ', '.join('%s since %s' % (c, tz(dn[c])) for c in sorted(dn))] if dn else ['Down Now: None']
    return cur + hist


def storage_check(st):
    now = time.time(); s = st.setdefault('store', {})
    if now - s.get('at', 0) < STORE_EVERY:
        return
    path = os.path.join(D, 'storage')
    try:
        du = shutil.disk_usage(path); free = du.free / du.total
    except Exception:
        return
    first = now
    try:
        days = sorted(x for x in os.listdir(os.path.join(path, 'recordings')) if re.match(r'\d{4}-\d{2}-\d{2}$', x))
        if days: first = calendar.timegm(time.strptime(days[0], '%Y-%m-%d'))
    except Exception:
        pass
    s['since'] = min(s.get('since', now), first)
    oldest = 0   # whole days back to the oldest kept alert (one small question per day, oldest day first)
    for d in range(40, -1, -1):
        try:
            r = get('/review?severity=alert&limit=1&after=%d&before=%d' % (int(now - (d + 1) * 86400), int(now - d * 86400)))
        except Exception:
            return   # Frigate busy: try again next minute
        if r:
            oldest = d + 1; break
    s.update(at=now, days=oldest, free=int(free * 100), gb=du.free // 2**30)
    why = []
    if free < STORE_FREE:
        why.append('Disk Free %d%%' % (free * 100))
    if now - s['since'] > (STORE_DAYS + 1) * 86400 and oldest < STORE_DAYS:
        why.append('Alerts Only Go Back %d Days' % oldest)
    if why and now - s.get('sent', 0) > 20 * 3600:
        ok = 'sent'
        try:
            req = urllib.request.Request(STORE_HOOK, data=json.dumps({'days': oldest, 'free': int(free * 100), 'gb': du.free // 2**30, 'why': ' · '.join(why)}).encode(), headers={'Content-Type': 'application/json'}, method='POST')
            urllib.request.urlopen(req, timeout=8).read()
        except Exception as x:
            ok = 'not sent (' + repr(x)[:80] + ')'
        s['sent'] = now
        log('storage alert %s: %s' % (ok, ' · '.join(why)))


def xiaomi_fix(dead, st):
    # restarts the xiaomi container when its camera is stuck (see XIAOMI_* above)
    xd = [c for c in dead if c in XIAOMI_CAMS]
    if not xd:
        st['xiaomi_runs'] = 0; return
    t10 = sh(['docker', 'logs', 'frigate', '--since', '10m'])
    trying = [c for c in xd if ('watchdog.%s ' % c) in t10 or ('ffmpeg.%s.' % c) in t10 or (': %s:' % c) in t10]
    if not trying:
        st['xiaomi_runs'] = 0; return
    st['xiaomi_runs'] = st.get('xiaomi_runs', 0) + 1
    if st['xiaomi_runs'] < XIAOMI_RUNS:
        return
    now = time.time(); day = [t for t in st.get('xiaomi_restarts', []) if now - t < 86400]
    if day and now - day[-1] < XIAOMI_GAP:
        return
    if len(day) >= XIAOMI_DAY:
        if not st.get('xiaomi_noted'):
            log('xiaomi stuck again (%s), not restarted: already 3 restarts today' % ', '.join(trying)); st['xiaomi_noted'] = 1
        return
    st['xiaomi_noted'] = 0
    log('restart xiaomi: no picture on %s for %d min' % (', '.join(trying), st['xiaomi_runs']))
    r = subprocess.run(['docker', 'restart', 'xiaomi'], capture_output=True, text=True, timeout=120)
    log('restart xiaomi done' if r.returncode == 0 else 'restart xiaomi failed: ' + (r.stderr or '').strip()[:150])
    st['xiaomi_restarts'] = day + [now]; st['xiaomi_runs'] = 0


def furbo_fix(dead, st):
    # restarts the furbo container when a Furbo camera is stuck (see FURBO_* above); returns nothing, logs what it did
    fd = [c for c in dead if 'furbo' in c and c not in released()]
    if not fd:
        st['furbo_runs'] = 0; return
    t10 = sh(['docker', 'logs', 'frigate', '--since', '10m'])
    trying = [c for c in fd if ('watchdog.%s ' % c) in t10 or ('ffmpeg.%s.' % c) in t10 or (': %s:' % c) in t10]
    fl = sh(['docker', 'logs', 'furbo', '--since', '2m']).lower()
    if not trying or not any(k in fl for k in FURBO_ERR):
        st['furbo_runs'] = 0; return
    st['furbo_runs'] = st.get('furbo_runs', 0) + 1
    if st['furbo_runs'] < FURBO_RUNS:
        return
    now = time.time(); day = [t for t in st.get('furbo_restarts', []) if now - t < 86400]
    if day and now - day[-1] < FURBO_GAP:
        return
    if len(day) >= FURBO_DAY:
        if not st.get('furbo_noted'):
            log('furbo stuck again (%s), not restarted: already 3 restarts today' % ', '.join(trying)); st['furbo_noted'] = 1
        return
    st['furbo_noted'] = 0
    log('restart furbo: no picture on %s, bridge errors for %d min' % (', '.join(trying), st['furbo_runs']))
    r = subprocess.run(['docker', 'restart', 'furbo'], capture_output=True, text=True, timeout=120)
    log('restart furbo done' if r.returncode == 0 else 'restart furbo failed: ' + (r.stderr or '').strip()[:150])
    st['furbo_restarts'] = day + [now]; st['furbo_runs'] = 0


def cpu_top(n=4):
    # the busiest programs right now (top's own snapshot, not lifetime averages), named so a person can read them:
    # an ffmpeg by the camera stream it reads (and whether go2rtc started it to re-encode), Frigate's parts by name.
    # Camera addresses and passwords never appear (only the stream name after the last slash).
    out = sh(['top', '-b', '-n', '1', '-c', '-o', '%CPU', '-w', '512'])
    rows, seen = [], False
    for line in out.splitlines():
        if not seen:
            seen = line.strip().startswith('PID'); continue
        f = line.split(None, 11)
        if len(f) < 12: continue
        try: cpu = float(f[8])
        except ValueError: continue
        cmd = f[11]
        if cmd.startswith('top ') or cpu < 3: continue
        if 'ffmpeg' in cmd:
            m = re.findall(r'(?:rtsp://|ffmpeg:)[^ ]*?/?([A-Za-z0-9_]+)(?:[?#][^ ]*)?(?= |$)', cmd)
            name = 'ffmpeg ' + (m[0] if m else '?') + (' re-encode' if 'go2rtc/ffmpeg' in cmd else '')
        elif 'go2rtc' in cmd: name = 'go2rtc'
        elif 'forkserver' in cmd: name = 'frigate cameras'
        elif cmd.startswith('frigate.'): name = cmd.split()[0]
        elif 'python3 -u -m frigate' in cmd: name = 'frigate main'
        elif 'furbo_p2p' in cmd: name = 'furbo bridge'
        else: name = os.path.basename(cmd.split()[0])
        rows.append('%s %d%%' % (name, round(cpu)))
        if len(rows) >= n: break
    return ', '.join(rows) or '?'


def health(dead, st, stats):
    # Mini PC Log for the app (Settings → Mini PC Log → Copy), written every minute, so the mini PC can be checked
    # from the phone without a terminal. Times in California time. Sections: Now, Last 10 Min, Hourly History (30 h),
    # Automatic Restarts, Update Log.
    now = datetime.now(TZ) if TZ else datetime.now()
    hk = now.strftime('%m-%d %Hh')
    L = ['Mini PC Log · ' + now.strftime('%m-%d %H:%M:%S'), '', '== Now ==']
    up = 0
    try:
        up = float(open('/proc/uptime').read().split()[0])
    except Exception: pass
    la = (open('/proc/loadavg').read().split()[:3] if os.path.exists('/proc/loadavg') else ['?'] * 3)
    temp = ''
    try:
        ts = [int(open(f).read()) / 1000 for f in __import__('glob').glob('/sys/class/thermal/thermal_zone*/temp')]
        if ts: temp = ' · CPU %d°C' % max(ts)
    except Exception: pass
    L.append('Mini PC Up %dd %dh · Load %s%s' % (up // 86400, up % 86400 // 3600, ' '.join(la), temp))
    mem = {}
    try:
        for line in open('/proc/meminfo'):
            k, v = line.split(':'); mem[k] = int(v.split()[0]) // 1024
        L.append('Memory Free %.1f GB of %.1f GB · Swap Used %d MB' % (mem['MemAvailable'] / 1024, mem['MemTotal'] / 1024, mem['SwapTotal'] - mem['SwapFree']))
    except Exception: pass
    try:
        du = shutil.disk_usage('/'); L.append('Disk Free %d GB of %d GB' % (du.free // 2**30, du.total // 2**30))
    except Exception: pass
    sto = st.get('store') or {}
    if 'days' in sto: L.append('Storage: Alerts Go Back %d Days · Recordings Disk Free %d%% (%d GB)' % (sto['days'], sto.get('free', 0), sto.get('gb', 0)))
    ps = sh(['docker', 'ps', '-a', '--format', '{{.Names}} {{.Status}}']).strip().splitlines()
    L.append('Containers: ' + (' · '.join(ps) if ps else '?'))
    a = started_ago()
    ver = ''
    try:
        ver = ' ' + str((stats or {}).get('service', {}).get('version', ''))
    except Exception: pass
    L.append('Frigate%s Up %s' % (ver, ('%d Hr %d Min' % (a // 3600, a % 3600 // 60)) if a < 1e8 else 'Not Running'))
    try:
        for k, v in ((stats or {}).get('gpu_usages') or {}).items(): L.append('GPU %s · Decode %s' % (v.get('gpu', '?'), v.get('dec', '?')))
        for k, v in ((stats or {}).get('detectors') or {}).items(): L.append('Detector %s %.1f ms' % (k, v.get('inference_speed', 0)))
    except Exception: pass
    L.append('No Frames: ' + (', '.join(dead) if dead else 'None'))
    L.append('Busiest Now: ' + cpu_top(6))
    t10 = sh(['docker', 'logs', 'frigate', '--since', '10m'])
    c10 = counts(t10)
    down = down_alerts(dead, st, t10)
    L += ['', '== Last 10 Min ==', 'Decode Errors: ' + top(c10['dec'], 8), 'Camera Crashes: ' + top(c10['crash'], 8), 'Recordings Discarded: ' + top(c10['disc'], 8)]
    cw = sh(['docker', 'logs', 'clipwait', '--since', '10m'])
    L.append('Notification Clips: %d Made · %d Failed' % (cw.count(' made '), cw.count('FAILED') + cw.count('failed')))
    # the last notification clip requests (camera, kind, made/cached, seconds, size or FAILED, who asked) and any
    # clip errors, from the last 3 hours, so a notification without its picture/video can be traced
    cw3 = []
    for l in sh(['docker', 'logs', '-t', 'clipwait', '--since', '3h']).splitlines():
        ts, _, msg = l.partition(' ')
        if not (msg.startswith('wait ') or 'failed' in msg.lower() or 'error' in msg.lower()):
            continue
        try:
            t = datetime.fromtimestamp(calendar.timegm(time.strptime(ts[:19], '%Y-%m-%dT%H:%M:%S')), TZ).strftime('%H:%M:%S')
        except Exception:
            t = ts[11:19]
        cw3.append(t + ' ' + msg[:150])
    L += ['', '== Notification Clips (Last 15 In 3 Hours) =='] + (cw3[-15:] or ['None'])
    # hourly history: this minute's new log lines added to the hour's bucket
    c1 = counts(sh(['docker', 'logs', 'frigate', '--since', '61s']))
    hist = st.setdefault('hist', {})
    h = hist.setdefault(hk, {'dec': {}, 'crash': {}, 'disc': {}, 'nofr': 0, 'load': 0, 'mem': 999, 'rs': 0})
    for k in ('dec', 'crash', 'disc'):
        for cam, n in c1[k].items(): h[k][cam] = h[k].get(cam, 0) + n
    h['nofr'] = max(h['nofr'], len(dead))
    try:
        if float(la[0]) >= h['load']:   # at the hour's busiest moment, note which programs were busy
            h['load'] = float(la[0]); h['top'] = cpu_top()
    except Exception: pass
    if mem: h['mem'] = min(h['mem'], mem['MemAvailable'] // 1024)
    for k in sorted(hist)[:-30]: del hist[k]
    L += ['', '== Hourly History (California Time) ==']
    for k in sorted(hist, reverse=True):
        x = hist[k]
        L.append('%s · Decode %d (%s) · Crashes %d · Discards %d · No Frames Max %d · Load Max %.1f · Memory Free Min %s GB%s' % (
            k, sum(x['dec'].values()), top(x['dec'], 3), sum(x['crash'].values()), sum(x['disc'].values()), x['nofr'], x['load'],
            x['mem'] if x['mem'] != 999 else '?', ' · Auto Restart' if x.get('rs') else '') + (' · Busiest: ' + x['top'] if x.get('top') else ''))
    try:
        w = open(LOG).read().strip().splitlines()[-10:]
    except Exception:
        w = []
    L += ['', '== Camera No Picture Alerts (Phone) =='] + (down or ['None'])
    L += ['', '== Automatic Restarts =='] + (w or ['None'])
    try:
        u = open(os.path.join(D, 'app', 'update-log.txt')).read().strip().splitlines()[-5:]
    except Exception:
        u = []
    L += ['', '== Update Log =='] + (u or ['None'])
    try:
        tmp = os.path.join(D, 'app', 'health.txt.tmp'); open(tmp, 'w').write('\n'.join(L) + '\n'); os.replace(tmp, os.path.join(D, 'app', 'health.txt'))
    except Exception: pass


def main():
    try:
        st = json.load(open(STATE))
    except Exception:
        st = {}
    st.setdefault('dead_runs', 0); st.setdefault('gpu_runs', 0); st.setdefault('api_runs', 0); st.setdefault('last_restart', 0)

    try:
        furbo360()
    except Exception as x:
        log('furbo 360 switch error: ' + repr(x)[:150])
    now_ca = datetime.now(TZ) if TZ else datetime.now()
    if now_ca.hour == DAILY_HOUR and now_ca.minute < 10 and time.time() - st.get('last_daily', 0) > 20 * 3600:
        st['last_daily'] = st['last_restart'] = time.time(); json.dump(st, open(STATE, 'w'))   # saved first: never twice
        log('daily restart: furbo, xiaomi, then frigate')
        for c in ('furbo', 'xiaomi'):
            r = subprocess.run(['docker', 'restart', c], capture_output=True, text=True, timeout=120)
            if r.returncode != 0: log('daily restart %s failed: %s' % (c, (r.stderr or '').strip()[:150]))
        time.sleep(20)
        r = subprocess.run(['docker', 'restart', 'frigate'], capture_output=True, text=True, timeout=180)
        log('daily restart done' if r.returncode == 0 else 'daily restart frigate failed: ' + (r.stderr or '').strip()[:150])
        return

    dead, why, stats = [], '', None
    if started_ago() < 600:          # just (re)started: give it time
        st.update(dead_runs=0, gpu_runs=0, api_runs=0)
        health([], st, None); json.dump(st, open(STATE, 'w')); return

    try:
        stats, cfg = get('/stats'), get('/config')
        st['api_runs'] = 0
        st['names'] = {cam: (c.get('friendly_name') or cam.replace('_', ' ').title()) for cam, c in (cfg.get('cameras') or {}).items()}
        for cam, c in (cfg.get('cameras') or {}).items():
            if c.get('enabled', True) is False:
                continue
            s = (stats.get('cameras') or {}).get(cam) or {}
            if (s.get('camera_fps') or 0) < 1:
                dead.append(cam)
        st['dead_runs'] = st['dead_runs'] + 1 if len(dead) >= 5 else 0
    except Exception:
        st['api_runs'] += 1

    g = gpu_errors()
    st['gpu_runs'] = st['gpu_runs'] + 1 if g >= 60 else 0

    # cameras without frames are only logged, never a reason to restart: cameras switched off by Camera Mode also give
    # no frames, and that restarted Frigate by mistake (white app while it restarted)
    if st['gpu_runs'] >= 5: why = f'graphics decode errors for 5 min ({g} in the last 2 min); no frames: {", ".join(dead) or "none"}'
    elif st['api_runs'] >= 5: why = 'Frigate API not answering for 5 min'

    if why and time.time() - st['last_restart'] > 1800:
        log('restart frigate: ' + why)
        r = subprocess.run(['docker', 'restart', 'frigate'], capture_output=True, text=True, timeout=180)
        log('restart done' if r.returncode == 0 else 'restart failed: ' + (r.stderr or '').strip()[:200])
        st.update(last_restart=time.time(), dead_runs=0, gpu_runs=0, api_runs=0)
        hk = (datetime.now(TZ) if TZ else datetime.now()).strftime('%m-%d %Hh'); st.setdefault('hist', {}).setdefault(hk, {'dec': {}, 'crash': {}, 'disc': {}, 'nofr': 0, 'load': 0, 'mem': 999})['rs'] = 1
    elif why and not st.get('noted'):
        log('would restart (waiting, restarted < 30 min ago): ' + why)
        st['noted'] = 1
    if not why:
        st['noted'] = 0
    if stats is not None and not why:
        furbo_fix(dead, st)
        xiaomi_fix(dead, st)
        storage_check(st)
    health(dead, st, stats)
    json.dump(st, open(STATE, 'w'))


if __name__ == '__main__':
    try:
        main()
    except Exception as x:   # never leave the app without a Mini PC Log: say what went wrong instead
        import traceback
        try:
            open(os.path.join(D, 'app', 'health.txt'), 'w').write('Mini PC Log · ' + time.strftime('%m-%d %H:%M UTC') + '\nWatchdog error: ' + repr(x) + '\n' + traceback.format_exc()[-600:])
        except Exception:
            pass
        log('watchdog error: ' + repr(x))
