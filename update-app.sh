#!/bin/sh
# Runs every minute on the mini PC (cron). Pulls the app and its web server config from GitHub.
R=https://raw.githubusercontent.com/yafengwy/victoria-camera-app/main
T=$(date +%s)
D=$HOME/frigate
curl -fsSL "$R/index.html?t=$T" -o /tmp/vh.html && [ -s /tmp/vh.html ] && cp /tmp/vh.html "$D/app/index.html"
if curl -fsSL "$R/app-nginx.conf?t=$T" -o /tmp/vh.conf && [ -s /tmp/vh.conf ] && ! cmp -s /tmp/vh.conf "$D/app-nginx.conf"; then
  cp /tmp/vh.conf "$D/app-nginx.conf" && docker exec vh-app nginx -s reload
fi
if curl -fsSL "$R/update-app.sh?t=$T" -o /tmp/vh.sh && [ -s /tmp/vh.sh ] && head -1 /tmp/vh.sh | grep -q '^#!/bin/sh' && ! cmp -s /tmp/vh.sh "$D/update-app.sh"; then
  cp /tmp/vh.sh "$D/update-app.sh" && chmod +x "$D/update-app.sh"
fi
