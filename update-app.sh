#!/bin/sh
# Runs every minute on the mini PC (cron). Pulls the app and its web server config from GitHub.
R=https://raw.githubusercontent.com/yafengwy/victoria-camera-app/main
T=$(date +%s)
D=$HOME/frigate
curl -fsSL "$R/index.html?t=$T" -o /tmp/vh.html && [ -s /tmp/vh.html ] && cp /tmp/vh.html "$D/app/index.html"
for f in icon-180.png icon-192.png icon-512.png manifest.webmanifest; do
  curl -fsSL "$R/$f?t=$T" -o "/tmp/vh-$f" && [ -s "/tmp/vh-$f" ] && cp "/tmp/vh-$f" "$D/app/$f"
done
if curl -fsSL "$R/app-nginx.conf?t=$T" -o /tmp/vh.conf && [ -s /tmp/vh.conf ] && ! cmp -s /tmp/vh.conf "$D/app-nginx.conf"; then
  cp /tmp/vh.conf "$D/app-nginx.conf" && docker exec vh-app nginx -s reload
fi
if curl -fsSL "$R/Caddyfile?t=$T" -o /tmp/vh.caddy && [ -s /tmp/vh.caddy ] && ! cmp -s /tmp/vh.caddy "$D/Caddyfile"; then
  cp /tmp/vh.caddy "$D/Caddyfile" && docker exec caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
fi
if curl -fsSL "$R/update-app.sh?t=$T" -o /tmp/vh.sh && [ -s /tmp/vh.sh ] && head -1 /tmp/vh.sh | grep -q '^#!/bin/sh' && ! cmp -s /tmp/vh.sh "$D/update-app.sh"; then
  cp /tmp/vh.sh "$D/update-app.sh" && chmod +x "$D/update-app.sh"
fi
