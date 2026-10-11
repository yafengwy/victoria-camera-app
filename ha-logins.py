#!/usr/bin/env python3
# New Home Assistant logins (her choice, 2026-10-11): runs every minute from update-app.sh on the mini PC.
# Asks Home Assistant which devices / browsers are logged in to Victoria's account (websocket auth/refresh_tokens,
# with the frigate token from ~/frigate/.env, which belongs to her account) and compares with the last minute.
# A new one sends one phone notification through the HA automation "Home Assistant Login Alert" (webhook, local
# network only): app or browser name, when, the IP and whether it is the home network or outside. A new long-lived
# token is reported the same way. The first run only remembers what is there (no notification).
# Failed logins are not done here: HA itself makes a "Login attempt failed" notice, and the same automation pushes it.
# Only her account is seen (the token is hers). Nothing is ever changed in Home Assistant.
import base64, json, os, socket, struct, sys, time
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo('America/Los_Angeles')
except Exception:
    TZ = None

D = os.path.expanduser('~/frigate')
STATE = os.path.join(D, '.ha-logins.json')
HA_HOST, HA_PORT = '192.168.1.252', 8123
HOOK = '/api/webhook/vh-ha-login-3f9c2a71d84e5b06'


def token():
    try:
        for ln in open(os.path.join(D, '.env')):
            if ln.startswith('FRIGATE_HA_TOKEN='):
                return ln.split('=', 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return ''


class WS:
    """The smallest websocket client that talks to Home Assistant (standard library only)."""
    def __init__(self, host, port, path):
        self.s = socket.create_connection((host, port), timeout=10)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall(('GET %s HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
                        'Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n' % (path, host, port, key)).encode())
        head = b''
        while b'\r\n\r\n' not in head:
            c = self.s.recv(1)
            if not c:
                raise IOError('closed during handshake')
            head += c
        if b' 101 ' not in head.split(b'\r\n', 1)[0]:
            raise IOError('no websocket: ' + head.split(b'\r\n', 1)[0].decode(errors='replace'))

    def _n(self, n):
        b = b''
        while len(b) < n:
            c = self.s.recv(n - len(b))
            if not c:
                raise IOError('closed')
            b += c
        return b

    def send(self, obj):
        p = json.dumps(obj).encode()
        h = bytes([0x81])
        n = len(p)
        h += bytes([0x80 | n]) if n < 126 else bytes([0x80 | 126]) + struct.pack('>H', n) if n < 65536 else bytes([0x80 | 127]) + struct.pack('>Q', n)
        m = os.urandom(4)
        self.s.sendall(h + m + bytes(b ^ m[i % 4] for i, b in enumerate(p)))

    def recv(self):
        data = b''
        while True:
            b0, b1 = self._n(2)
            n = b1 & 0x7F
            if n == 126:
                n = struct.unpack('>H', self._n(2))[0]
            elif n == 127:
                n = struct.unpack('>Q', self._n(8))[0]
            m = self._n(4) if b1 & 0x80 else None
            p = self._n(n)
            if m:
                p = bytes(b ^ m[i % 4] for i, b in enumerate(p))
            op = b0 & 0x0F
            if op == 8:
                raise IOError('closed by Home Assistant')
            if op == 9:      # ping → pong
                self.s.sendall(bytes([0x8A, 0x80]) + os.urandom(4))
                continue
            if op in (1, 0):
                data += p
                if b0 & 0x80:
                    return json.loads(data)

    def close(self):
        try:
            self.s.sendall(bytes([0x88, 0x80]) + os.urandom(4))
        except OSError:
            pass
        self.s.close()


def tokens(tk):
    ws = WS(HA_HOST, HA_PORT, '/api/websocket')
    try:
        ws.recv()                                          # auth_required
        ws.send({'type': 'auth', 'access_token': tk})
        a = ws.recv()
        if a.get('type') != 'auth_ok':
            raise IOError('token refused: ' + str(a.get('type')))
        ws.send({'id': 1, 'type': 'auth/refresh_tokens'})
        while True:
            r = ws.recv()
            if r.get('id') == 1:
                if not r.get('success'):
                    raise IOError('refresh_tokens refused: ' + json.dumps(r.get('error')))
                return r.get('result') or []
    finally:
        ws.close()


def home_ip(ip):
    ip = (ip or '').strip()
    if not ip:
        return None
    if ip.startswith(('192.168.', '10.', '127.', '::1', 'fe80', 'fd', 'fc')):
        return True
    if ip.startswith('172.'):
        try:
            return 16 <= int(ip.split('.')[1]) <= 31
        except ValueError:
            return False
    return False


def app_name(t):
    if t.get('type') == 'long_lived_access_token':
        return '长期访问令牌 ' + (t.get('client_name') or '')
    n = t.get('client_name') or ''
    cid = (t.get('client_id') or '').lower()
    if 'ios' in cid:
        return n or 'Home Assistant iPhone / iPad App'
    if 'android' in cid:
        return n or 'Home Assistant Android App'
    if 'google' in cid:
        return n or 'Google'
    if 'amazon' in cid or 'alexa' in cid:
        return n or 'Alexa'
    return n or ('浏览器 ' + (t.get('client_id') or ''))


def local(iso):
    try:
        d = datetime.fromisoformat(iso.replace('Z', '+00:00'))
        return d.astimezone(TZ).strftime('%m-%d %H:%M') if TZ else d.strftime('%m-%d %H:%M UTC')
    except Exception:
        return iso or ''


def notify(t):
    import urllib.request
    ip = t.get('last_used_ip') or ''
    h = home_ip(ip)
    body = {'app': app_name(t).strip(), 'when': local(t.get('created_at') or ''), 'ip': ip or '不知道',
            'where': '家里网络' if h else ('外网' if h is False else '不知道')}
    req = urllib.request.Request('http://%s:%d%s' % (HA_HOST, HA_PORT, HOOK), data=json.dumps(body, ensure_ascii=False).encode(),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    urllib.request.urlopen(req, timeout=10).read()
    return body


def main():
    tk = token()
    if not tk:
        return
    try:
        st = json.load(open(STATE))
    except Exception:
        st = {}
    try:
        ts = tokens(tk)
    except Exception as e:
        # one line an hour at most, so a Home Assistant restart does not fill the log
        if time.time() - st.get('err_at', 0) > 3600:
            print(time.strftime('%m-%d %H:%M ') + 'ha-logins: ' + str(e)[:200])
            st['err_at'] = time.time()
            json.dump(st, open(STATE, 'w'))
        return
    now = {t['id']: t for t in ts if t.get('id')}
    known = st.get('ids')
    if known is None:
        st['ids'] = sorted(now)
        json.dump(st, open(STATE, 'w'))
        print(time.strftime('%m-%d %H:%M ') + 'ha-logins: first run, %d logged in' % len(now))
        return
    def age(t):
        try:
            return time.time() - datetime.fromisoformat((t.get('created_at') or '').replace('Z', '+00:00')).timestamp()
        except Exception:
            return 9999
    # a login seen before its first use has no IP yet: wait for it (up to 3 minutes), then report it anyway
    wait = [i for i in now if i not in set(known) and not now[i].get('last_used_ip') and age(now[i]) < 180]
    new = [now[i] for i in now if i not in set(known) and i not in wait]
    st['ids'] = sorted(i for i in now if i not in wait)      # saved first: never twice
    json.dump(st, open(STATE, 'w'))
    for t in new:
        try:
            b = notify(t)
            print(time.strftime('%m-%d %H:%M ') + 'ha-logins: new %s · %s · %s' % (b['app'], b['ip'], b['where']))
        except Exception as e:
            print(time.strftime('%m-%d %H:%M ') + 'ha-logins: notify failed ' + str(e)[:200])


if __name__ == '__main__':
    main()
