#!/bin/sh
# Once a day: copy Frigate's config into Victoria's private GitHub repo yafengwy/frigate-config-backup,
# so an older version can always be brought back. Run by update-app.sh every minute; does nothing until the
# key file exists, and only once per day after that.
# The key lives only on the mini PC, in ~/frigate/backup-token: a GitHub token that may write that one repo.
# It is sent as a header, never written into a URL or a log.
D=$HOME/frigate
B=$D/config-backup
R=https://github.com/yafengwy/frigate-config-backup.git
T=$(tr -d ' \r\n' < "$D/backup-token" 2>/dev/null)
[ -n "$T" ] || exit 0
day=$(date +%Y-%m-%d)
[ "$(cat "$D/.backup-day" 2>/dev/null)" = "$day" ] && exit 0
# after a failure, try again an hour later (not every minute)
w=$(cat "$D/.backup-wait" 2>/dev/null); [ -n "$w" ] && [ $(( $(date +%s) - w )) -lt 3600 ] && exit 0
fail() { date +%s > "$D/.backup-wait"; echo "$(date "+%m-%d %H:%M") backup: $1"; exit 0; }
H="Authorization: Basic $(printf 'x-access-token:%s' "$T" | base64 | tr -d '\n')"
g() { git -C "$B" -c http.extraHeader="$H" "$@"; }
if [ ! -d "$B/.git" ]; then
  git -c http.extraHeader="$H" clone -q "$R" "$B" 2>/dev/null || fail "cannot reach the backup repo (check the key)"
fi
g pull -q --rebase origin main 2>/dev/null
for f in config.yml config.yaml; do [ -s "$D/config/$f" ] && cp "$D/config/$f" "$B/$f"; done
[ -s "$D/docker-compose.yml" ] && cp "$D/docker-compose.yml" "$B/docker-compose.yml"
g add -A
g -c user.name="Mini PC" -c user.email="backup@victoriashome.app" commit -q -m "Backup $day" >/dev/null 2>&1
if g push -q origin HEAD:main 2>/dev/null; then
  echo "$day" > "$D/.backup-day"; rm -f "$D/.backup-wait"; echo "$(date "+%m-%d %H:%M") backup ok"
else
  fail "push failed (check the key)"
fi
