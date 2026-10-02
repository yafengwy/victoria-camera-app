#!/bin/sh
# Runs every minute on the mini PC (cron). Keeps a git copy of the repo and installs any changes:
# the app, its icons, and the web server / outside-access configs (reloading them only when they change).
# Uses git instead of raw.githubusercontent.com, whose 5-minute cache served old files.
D=$HOME/frigate
G=$D/repo
[ -d "$G/.git" ] || git clone -q --depth 1 https://github.com/yafengwy/victoria-camera-app "$G" || exit 0
git -C "$G" fetch -q --depth 1 origin main && git -C "$G" reset -q --hard origin/main || exit 0
for f in index.html icon-180.png icon-192.png icon-512.png manifest.webmanifest; do
  [ -s "$G/$f" ] && ! cmp -s "$G/$f" "$D/app/$f" && cp "$G/$f" "$D/app/$f"
done
if [ -s "$G/app-nginx.conf" ] && ! cmp -s "$G/app-nginx.conf" "$D/app-nginx.conf"; then
  cp "$G/app-nginx.conf" "$D/app-nginx.conf" && docker exec vh-app nginx -s reload
fi
if [ -s "$G/Caddyfile" ] && ! cmp -s "$G/Caddyfile" "$D/Caddyfile"; then
  cp "$G/Caddyfile" "$D/Caddyfile" && docker exec caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
fi
if head -1 "$G/update-app.sh" | grep -q '^#!/bin/sh' && ! cmp -s "$G/update-app.sh" "$D/update-app.sh"; then
  cp "$G/update-app.sh" "$D/update-app.sh" && chmod +x "$D/update-app.sh"
fi
