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
import calendar, json, os, subprocess, time, urllib.request

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


def main():
    try:
        st = json.load(open(STATE))
    except Exception:
        st = {}
    st.setdefault('dead_runs', 0); st.setdefault('gpu_runs', 0); st.setdefault('api_runs', 0); st.setdefault('last_restart', 0)

    if started_ago() < 600:          # just (re)started: give it time
        st.update(dead_runs=0, gpu_runs=0, api_runs=0)
        json.dump(st, open(STATE, 'w')); return

    dead, why = [], ''
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


if __name__ == '__main__':
    main()
