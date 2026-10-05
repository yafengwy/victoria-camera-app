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


def health(dead, st, stats):
    # Mini PC health for the app: copied together with the Playback Log (Settings → Copy), so problems can be read
    # without a terminal. Times in California time.
    now = datetime.now(TZ) if TZ else datetime.now()
    L = ['Mini PC Health · ' + now.strftime('%m-%d %H:%M:%S')]
    try:
        la = open('/proc/loadavg').read().split()[:3]; L.append('Load ' + ' '.join(la))
    except Exception: pass
    try:
        du = shutil.disk_usage('/'); L.append('Disk Free %d GB of %d GB' % (du.free // 2**30, du.total // 2**30))
    except Exception: pass
    a = started_ago(); L.append('Frigate Up ' + (('%d Hr %d Min' % (a // 3600, a % 3600 // 60)) if a < 1e8 else 'Not Running'))
    try:
        g = (stats or {}).get('gpu_usages') or {}
        for k, v in g.items(): L.append('GPU %s · Decode %s' % (v.get('gpu', '?'), v.get('dec', '?')))
    except Exception: pass
    L.append('No Frames: ' + (', '.join(dead) if dead else 'None'))
    try:
        out = subprocess.run(['docker', 'logs', 'frigate', '--since', '10m'], capture_output=True, text=True, timeout=20)
        cnt = {}
        for line in (out.stdout + out.stderr).splitlines():
            if any(k in line for k in ('Failed to sync surface', 'hardware accelerator failed', 'Failed to download frame', 'Missing reference')):
                m = re.search(r'ffmpeg\.([a-z0-9_]+)\.', line)
                if m: cnt[m.group(1)] = cnt.get(m.group(1), 0) + 1
        L.append('Decode Errors 10 Min: ' + (', '.join('%s %d' % kv for kv in sorted(cnt.items(), key=lambda x: -x[1])) if cnt else 'None'))
    except Exception: pass
    try:
        w = open(LOG).read().strip().splitlines()[-6:]
        L.append('Auto Restarts: ' + (' | '.join(w) if w else 'None'))
    except Exception:
        L.append('Auto Restarts: None')
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
        json.dump(st, open(STATE, 'w')); health([], st, None); return

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
    elif why and not st.get('noted'):
        log('would restart (waiting, restarted < 30 min ago): ' + why)
        st['noted'] = 1
    if not why:
        st['noted'] = 0
    json.dump(st, open(STATE, 'w'))
    health(dead, st, stats)


if __name__ == '__main__':
    main()
