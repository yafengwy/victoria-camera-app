#!/bin/sh
# Runs every minute on the mini PC (cron). Keeps a git copy of the repo and installs any changes:
# the app, its icons, and the web server / outside-access configs (reloading them only when they change).
# Uses git instead of raw.githubusercontent.com, whose 5-minute cache served old files.
D=$HOME/frigate
G=$D/repo
L=$D/app/update-log.txt
exec 2>>"$L"
[ "$(wc -c < "$L" 2>/dev/null || echo 0)" -gt 20000 ] && tail -c 10000 "$L" > "$L.tmp" && mv "$L.tmp" "$L"
[ -d "$G/.git" ] || git clone -q --depth 1 https://github.com/yafengwy/victoria-camera-app "$G" || exit 0
git -C "$G" fetch -q --depth 1 origin main && git -C "$G" reset -q --hard origin/main || exit 0
for f in index.html version.txt icon-180.png icon-192.png icon-512.png manifest.webmanifest; do
  [ -s "$G/$f" ] && ! cmp -s "$G/$f" "$D/app/$f" && cp "$G/$f" "$D/app/$f"
done
# Reload only counts once it succeeded (.applied-* copies), so a failed reload is retried next minute
if [ -s "$G/app-nginx.conf" ] && ! cmp -s "$G/app-nginx.conf" "$D/.applied-nginx"; then
  cp "$G/app-nginx.conf" "$D/app-nginx.conf" && { echo "$(date "+%m-%d %H:%M") nginx reload"; docker exec vh-app nginx -s reload; } >&2 && cp "$G/app-nginx.conf" "$D/.applied-nginx" && echo "$(date "+%m-%d %H:%M") nginx ok" >&2
fi
if [ -s "$G/Caddyfile" ] && ! cmp -s "$G/Caddyfile" "$D/.applied-caddy"; then
  cp "$G/Caddyfile" "$D/Caddyfile" && docker exec caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile && cp "$G/Caddyfile" "$D/.applied-caddy"
fi
if [ -s "$G/docker-compose.yml" ] && ! cmp -s "$G/docker-compose.yml" "$D/.applied-compose"; then
  cp "$G/docker-compose.yml" "$D/docker-compose.yml" && (cd "$D" && docker compose up -d) && cp "$G/docker-compose.yml" "$D/.applied-compose"
fi
# Connection check the app shows in Settings (Frigate version, and whether a websocket handshake to /ws answers,
# directly on Frigate and through the app's web server)
{
  echo "Frigate $(curl -s -m 3 http://localhost:5000/api/version)"
  for u in http://localhost:5000/ws http://localhost:8080/ws; do
    r=$(curl -s -i -m 4 -N -H "Connection: Upgrade" -H "Upgrade: websocket" -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" "$u" 2>&1 | head -1 | tr -d "\r")
    echo "$u -> ${r:-no answer}"
  done
} > "$D/app/diag.txt" 2>&1
if head -1 "$G/update-app.sh" | grep -q '^#!/bin/sh' && sh -n "$G/update-app.sh" && ! cmp -s "$G/update-app.sh" "$D/update-app.sh"; then
  # new file + rename, so the copy of this script that is still running is not overwritten under it
  cp "$G/update-app.sh" "$D/update-app.sh.new" && chmod +x "$D/update-app.sh.new" && mv -f "$D/update-app.sh.new" "$D/update-app.sh"
fi
