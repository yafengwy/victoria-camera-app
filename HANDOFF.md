# Handoff: Victoria's Home camera app

Read this first when picking the app up in a new conversation. No secrets live in this repo (it is public).

## Working rules (Victoria)
- Reply in Chinese, short and direct. Spell out every terminal step: say whether a block is pasted as one command or line by line.
- Push fixes right away (commit + push; the mini PC pulls every minute).
- Mockups (示意图) are images only, until she confirms. Don't touch the app for mockups.
- Every UI label starts with a capital letter, including each "·"-separated part.
- For Frigate changes, prefer steps in the Frigate web UI over editing the config file.
- Version rule: the 2nd and 3rd numbers go 1..10, then roll over (1.5.10 → 1.6.1). `build.py release` does this.
- Before delivering, check that nothing is counted twice and that earlier behaviour still holds. Find the real root cause; she uploads logs (Settings → copy log) instead of describing.
- Use only her GitHub account (yafengwy). Never ask her to post tokens or passwords; ask her to mask them in screenshots.

## Layout
- `index.html`: the built app that is served. Don't edit it by hand. It is produced from `dev/src/index.html`.
- `dev/src/index.html`: the source (one file: HTML, CSS and JS).
- `dev/build.py`: `python3 build.py` writes `preview.html`; `python3 build.py release` bumps `ver.txt` first.
- **Release**: from `dev/`, run `python3 build.py release`, then `cp preview.html ../index.html && cp ver.txt ../version.txt`, then commit and push.
- `dev/mock/srv2.py`: a fake Frigate on 127.0.0.1:8765 serving `index.html` from its own folder (copy `preview.html` there first).
  - It needs `front_s.jpg` (any jpg) and a `vod9/` HLS fMP4 folder (`index.m3u8` + segments). Make one with an ffmpeg testsrc.
  - Tests `t*.js` use Playwright with `executablePath: '/opt/pw-browsers/chromium'`; run with `NODE_PATH=<node_modules>`.
  - Regression set: t38 t40 t42 t53 t56 t61 t66 t67 t69 t70 t72 t73 t74 t76 t77.
- `update-app.sh`: cron on the mini PC every minute. It pulls this repo and copies the app files, nginx, Caddy, compose and clipwait. It also runs `backup-config.sh` (daily Frigate config backup to private repo yafengwy/frigate-config-backup; working since 2026-10-03, token expires 2027-10-03).
- `app-nginx.conf`, `Caddyfile`, `docker-compose.yml`, `clipwait.py`, `furbo-go2rtc.yaml`: server side.
- Secrets exist only on the mini PC: `~/frigate/.env`, `caddy.env`, `ha-auth.conf`, `furbo-auth.conf`, `furbo-data/options.json`, `backup-token`.

## Server facts
- Mini PC user `victoria-frigate`, folder `~/frigate`. Frigate 0.18 runs in Docker; the app is container `vh-app` (nginx).
- Public: `cam.victoriashome.app` (the app) and `frigate.victoriashome.app` (Frigate UI). Home Assistant runs separately on HA Yellow.
- HA has **no** Frigate integration. HA talks to Frigate over MQTT (for example `frigate/<cam>/enabled/set`).
- Recording: continuous 0 days, motion 7 days, segment_time 5. Alerts retention mode was set to All globally on 2026-10-03, so alerts keep their full video.
- Litter Box 猫砂盆 (Xiaomi isa.camera.hlc7, 192.168.1.84): separate `xiaomi` go2rtc container on the host network (xiaomi-go2rtc.yaml, RTSP 8574); Frigate pulls rtsp://xiaomi:{FRIGATE_CAM_PW}@192.168.1.77:8574/litter_box. Token XIAOMI_TOKEN in .env. Notifies always, all animals.
- Treat Feeder (CloudEdge/Meari): a go2rtc `echo:curl` to HA `/api/camera_stream_source/<entity>` (HA token from `.env`). It needs `GO2RTC_ALLOW_ARBITRARY_EXEC=true` in `.env` (added 2026-10-03).

## Camera rules (as of 1.5.10)
- 4 Furbos (upstairs, bedroom, fishtofu = 胖胖饭桶, riceball = 团团饭桶) and treat_feeder: track and alert cat, dog, bird only, never person.
- fishtofu and riceball never notify, but their alerts still show as Interesting.
- The HA automation "Camera Mode Indoor Cameras" turns these off At Home: entry_room, living_room, prep_kitchen, upstairs_living, upstairs_furbo, bedroom_furbo, treat_feeder and nest_master_bedroom.
- HA notifications go out for alerts only.
- Home order is the `ORDER` list in `Frigate.load()`; treat_feeder sits before living_room.

## App map (search these names in dev/src/index.html)
- `Snd` (sound), `FZ` (full-screen zoom).
- Downloads: `SaveBar`, `fetchWithBar`, `deliver`, `saveClip`.
- `TG`: document-level guard so a drag end on iOS is not taken as a tap.
- Pictures for past times: `RecMap`, `recFail`, `recMiss`, `alertTry`, `NOREC` / `LOADFAIL`.
- Review page: `paintReview`, `drawRvTrack`, `rvRefine`, `rvBarCompact`.
- Wide Alerts page (at least 1000px): `evWide`.
- Camera-view clip: `fclip*`.
- Home Live button (#livebtn, ACT.live1): tap = this camera live; double tap = all cameras live.
- Header button order everywhere: Power, Date, Boxes, Sound, Live (Live rightmost). Grid panel puts the same set at its right; on narrow phones (≤600px) it is Power, Sound | Play/Pause | Boxes, Date, Live. Panel has only Play/Pause (no previous/next).
- Wide grids (3+ per row): panel is 2 columns wide; cameras pair up (1–2 → columns 1–2, 3–4 → 3–4, last odd one → last two) (`.grid.dense`, `panel(c, col)`). Panel spacing compacted in v71 CSS block.

## Open items
- iPhone Duo cover screen: she has not received the phone yet; screenshots pending. (She also uses a Galaxy Z Flip.)
- Xiaomi / Aqara cameras: waiting for model numbers.
- Prep Kitchen WiFi question.
- Offered: change the "No Recording" subtitle to "Not Saved By Frigate" on tiles that do have an alert.
- Review layouts (Grid uses the same order too): only Big and Grid (Alerts On Top merged into Big). Big by screen: wide (side timeline) big 2x2 on the left, 4-5 columns; phones and upright tablets big across the top, 2 (phone) / 3 (tablet) per row below. Order: picture first, Interesting, Uninteresting, rest, then No Recording. Adjust per device when she reports a new width.
- Review alert list (bell, S.rv.list, rvListHtml/rvlpick): replaces the timeline; phone bottom 38vh list, wide 340px right column; follows the alert filter.
