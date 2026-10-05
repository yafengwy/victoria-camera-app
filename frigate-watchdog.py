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
    c10 = counts(sh(['docker', 'logs', 'frigate', '--since', '10m']))
    L += ['', '== Last 10 Min ==', 'Decode Errors: ' + top(c10['dec'], 8), 'Camera Crashes: ' + top(c10['crash'], 8), 'Recordings Discarded: ' + top(c10['disc'], 8)]
    cw = sh(['docker', 'logs', 'clipwait', '--since', '10m'])
    L.append('Notification Clips: %d Made · %d Failed' % (cw.count(' made '), cw.count('FAILED') + cw.count('failed')))
    # hourly history: this minute's new log lines added to the hour's bucket
    c1 = counts(sh(['docker', 'logs', 'frigate', '--since', '61s']))
    hist = st.setdefault('hist', {})
    h = hist.setdefault(hk, {'dec': {}, 'crash': {}, 'disc': {}, 'nofr': 0, 'load': 0, 'mem': 999, 'rs': 0})
    for k in ('dec', 'crash', 'disc'):
        for cam, n in c1[k].items(): h[k][cam] = h[k].get(cam, 0) + n
    h['nofr'] = max(h['nofr'], len(dead))
    try: h['load'] = max(h['load'], float(la[0]))
    except Exception: pass
    if mem: h['mem'] = min(h['mem'], mem['MemAvailable'] // 1024)
    for k in sorted(hist)[:-30]: del hist[k]
    L += ['', '== Hourly History (California Time) ==']
    for k in sorted(hist, reverse=True):
        x = hist[k]
        L.append('%s · Decode %d (%s) · Crashes %d · Discards %d · No Frames Max %d · Load Max %.1f · Memory Free Min %s GB%s' % (
            k, sum(x['dec'].values()), top(x['dec'], 3), sum(x['crash'].values()), sum(x['disc'].values()), x['nofr'], x['load'],
            x['mem'] if x['mem'] != 999 else '?', ' · Auto Restart' if x.get('rs') else ''))
    try:
        w = open(LOG).read().strip().splitlines()[-10:]
    except Exception:
        w = []
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

    dead, why, stats = [], '', None
    if started_ago() < 600:          # just (re)started: give it time
        st.update(dead_runs=0, gpu_runs=0, api_runs=0)
        health([], st, None); json.dump(st, open(STATE, 'w')); return

    try:
        stats, cfg = get('/stats'), get('/config')
        st['api_runs'] = 0
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

    if st['dead_runs'] >= 5: why = f'{len(dead)} cameras without frames for 5 min: {", ".join(dead)}'
    elif st['gpu_runs'] >= 5: why = f'graphics decode errors for 5 min ({g} in the last 2 min); no frames: {", ".join(dead) or "none"}'
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
    health(dead, st, stats)
    json.dump(st, open(STATE, 'w'))


if __name__ == '__main__':
    main()
