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
- `update-app.sh`: cron on the mini PC every minute. It pulls this repo and copies the app files, nginx, Caddy, compose and clipwait, and restarts the xiaomi go2rtc when xiaomi-go2rtc.yaml changes. It also runs `backup-config.sh` (daily Frigate config backup to private repo yafengwy/frigate-config-backup; working since 2026-10-03, token expires 2027-10-03).
- `app-nginx.conf`, `Caddyfile`, `docker-compose.yml`, `clipwait.py`, `furbo-go2rtc.yaml`: server side.
- Secrets exist only on the mini PC: `~/frigate/.env`, `caddy.env`, `ha-auth.conf`, `furbo-auth.conf`, `furbo-data/options.json`, `backup-token`.

## Server facts
- Mini PC user `victoria-frigate`, folder `~/frigate`. Frigate 0.18 runs in Docker; the app is container `vh-app` (nginx).
- Public: `cam.victoriashome.app` (the app) and `frigate.victoriashome.app` (Frigate UI). Home Assistant runs separately on HA Yellow.
- HA has **no** Frigate integration. HA talks to Frigate over MQTT (for example `frigate/<cam>/enabled/set`).
- Recording: continuous 0 days, motion 7 days, segment_time 5. Alerts retention mode was set to All globally on 2026-10-03, so alerts keep their full video.
- Litter Box 猫砂盆 (Xiaomi isa.camera.hlc7, 192.168.1.84): separate `xiaomi` go2rtc container on the host network (xiaomi-go2rtc.yaml, RTSP 8574); Frigate pulls rtsp://xiaomi:{FRIGATE_CAM_PW}@192.168.1.77:8574/litter_box. Token XIAOMI_TOKEN in .env. Notifies always, all animals. Uses `&subtype=sd&transport=tcp`: cs2 over UDP kept timing out on its WiFi; without a fixed subtype the camera switched between 2K and 640x360 by itself, which zoomed recorded playback. Changing the stream resolution needs `docker restart frigate`, or Live goes green. Frigate camera_fps 5 is just detect fps; check the source rate in the xiaomi go2rtc API (about 20).
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
- 2026-10-04 progress: (1) Furbo done (see below). Face: no recognition attempts at all because detect is 640x360 and faces were under the 750 px default; set face_recognition.min_area: 300 and added face to the 5 indoor cameras — check Recent Recognitions fills, then retest Teach. Earlier list: (1) Furbo VAAPI re-encode (go2rtc <name>_raw + ffmpeg:...#video=h264#hardware) gave all 4 Furbos no picture; she reverted. Check Frigate logs / go2rtc stream state, fix, so iPhone can play Furbo recordings. (2) Who? with Teach ticked did not add faces to Frigate's Face Library: check Frigate logs for POST /api/faces/train/<name>/classify status and the toast she saw. (3) Add face to the tracked objects of entry_room, living_room, prep_kitchen, upstairs_living, nest_master_bedroom so indoor alerts show Victoria / James (face library is shared). (4) Boxes lag objects; 1.9.3 fix (segment-aligned alert clips + annotation offset) made boxes vanish on her iPhone; find out why before re-releasing.
- Next: back up the Frigate+ model files in ~/frigate/config/model_cache (not in the daily config backup). She decided not to rotate the notify key.
- In ~2 days: per-day recording sizes → decide on a 2TB M.2 SSD (EQi13 has a free M.2 2280 slot); face recognition is on (Train tab).
- Driveway Enter Line: car false alerts from headlights reflecting on a window (3-5 s). First watch with the Frigate+ model; if it continues, draw a car-only Object Mask over that window (needs a screenshot of a false alert with its box).
- iPhone Duo cover screen: the phone arrives in November; nothing to do before then. (She also uses a Galaxy Z Flip.)
- Xiaomi / Aqara cameras: waiting for model numbers.
- Offered: change the "No Recording" subtitle to "Not Saved By Frigate" on tiles that do have an alert.
- Review layouts (Grid uses the same order too): only Big and Grid (Alerts On Top merged into Big). Big by screen: wide (side timeline) big 2x2 on the left, 4-5 columns; phones and upright tablets big across the top, 2 (phone) / 3 (tablet) per row below. Order: picture first, Interesting, Uninteresting, rest, then No Recording. Adjust per device when she reports a new width.
- Review alert list (bell, S.rv.list, rvListHtml/rvlpick): replaces the timeline; phone bottom 38vh list, wide 340px right column; follows the alert filter.
- Settings → Version (tap to open) → "Frigate Log · Last 2 Hrs" Copy: fetches /api/logs/frigate and copies restarts, camera reconnects, recording lines and errors from the last 2 hours (local times). Use it when an alert has no recording. Frigate clears this log when its container is rebuilt.
- Today's Waiting (1.8.3): More menu → pick Amazon/USPS/UPS/FedEx/DHL and an end time. Stored in HA input_text.camera_waiting as "FROM|UNTIL|ups,fedex" (read via /ha/waiting, set via /ha/snoozeset). The app marks a car whose Frigate+ logo sub label matches as Interesting (label shows the company); each phone keeps past waits 30 days. HA automation "Camera Waiting Delivery" (MQTT frigate/reviews) sends the notification.
- Frigate+ (bought 2026-10-04): model yolov9s 320x320 base 2026.2 (plus://19e725aa90b9063fdce57fdcd7132ee5), PLUS_API_KEY in .env.
- HA Camera Notifications (2026-10-04): At Home, Closet/Garage1/Garage2/California Room notify for any of cat, dog, raccoon, rabbit, squirrel, fox; while input_boolean.gardener_3_hrs is on, Front Door, Driveway, Right Yard Front, Right Yard Back, Backyard, Left Yard and California Room send no camera notifications (sound notifications and Today's Waiting still do). Notification Silence buttons were offered and declined.
- People (1.8.5): alerts show "Person · Name" / "Car · UPS" (lab(e), ico(e)); names come from review sub_labels (face recognition) and from person events' sub_label (People.loadSubs, /api/events?labels=person). Alert cards with a person have "Who?": sets the sub label on the person events (POST /api/events/<id>/sub_label, X-CSRF-TOKEN header) and can teach face recognition (POST /api/faces/train/<name>/classify {event_id}). More → People: Frigate's face library (/api/faces): new faces from Train can be named or deleted; known people listed. Face/logo/license_plate labels are attributes and never appear as filter objects.
- Delete alert (1.9.2): trash button on Alerts cards → confirm → DELETE /api/events/ {event_ids} then POST /api/reviews/delete {ids} (Frigate also deletes that camera's recordings overlapping the alert). Other cameras' video of the same moment is not touched.
- Furbo playback on iPhone (fixed 2026-10-04 ~12:00): the bridge's stream switches between 1280x720 and 640x360 mid-recording (WebRTC adaptive), which iPhone can't decode. Frigate go2rtc now has <name>_raw (bridge RTSP) + <name>: ffmpeg:<name>_raw#video=h264#width=1280#height=720 (software encode; the #hardware VAAPI version gave no picture). New segments verified all 1280 wide; recordings from before the change still won't play on iPhone.
- Boxes (1.9.3, rolled back in 1.9.4 because she saw no boxes at all on the iPhone; redo carefully): alert-card clips start on a recording piece (like the camera player) and keep a clip-second → clock map (v._win), and every box lookup subtracts the camera's Frigate detect.annotation_offset (Data.cam().aoff), so boxes follow objects; tune the offset per camera in Frigate's Explore → Tracking Details → Annotation Settings.
- Boxes 2.1.6: only the annotation offset part is back (Data.cam().aoff from detect.annotation_offset; box lookup uses video time − aoff). The alert-card segment-aligned clip part (v._win) stays out until tested on her iPhone. She tunes the offset per camera in Frigate (Explore → Tracking Details → Annotation Settings). 2026-10-04: notification cooldown 1 min per camera added (input_text.camera_notify_last, 'cam=ts;cam=ts'); model_cache backed up to ~/model_cache_backup_2026-10-04. 2026-10-04: she checked Front Door/Driveway boxes in Frigate Explore, they line up, offset left as is; Doorbell added to the Gardener Mode quiet list (and name map → Doorbell) in Camera Notifications.
- November (reminder set for 2026-11-02 9am PT): ask if the 4 Furbos still have problems; if not, remove the Furbo log section from Settings. Also check the iPhone Duo cover layout then.
- 2026-10-04 baseline before Front Door detect change: load 7.5/6.6/6.7, 18 GiB RAM free of 23, frigate 622% CPU / 4.75 GiB, OpenVINO inference 20.3 ms, front_door process 18.7%. Front Door streams: subtype=1 1200x536 HEVC (current detect, also front_door_sub used by app grid), subtype=2 1920x860 HEVC. Done 2026-10-04 15:00: go2rtc front_door_detect (subtype=2) is the detect+audio input, verified scale_vaapi w=1920:h=860 (no detect block, size is automatic); front_door_sub stays for the app grid. Check again 2026-10-06 (reminder set).
- 2026-10-04 Nest Doorbell added (nest_doorbell, real picture 3:4 portrait 384x512; the stream carries a wrong sample-aspect flag so browsers show it 683x512 squashed; Frigate detect 720x960; app stretches the video back to 3:4 (.door object-fit:fill), WEB_RTC; FRIGATE_NEST_DOORBELL in .env). The ffmpeg re-encode (_raw + #video=h264#hardware) fails for it (Invalid data). Working setup: direct nest: source; camera ffmpeg global_args add -max_error_rate 1.0; input_args -avoid_negative_ts make_zero -fflags +genpts+discardcorrupt -rtsp_transport tcp -timeout 10000000 -analyzeduration 10000000 -probesize 10000000; detect 1920x1080. ~4 fps; ffmpeg still restarts now and then (no SPS after the Nest WebRTC stream renews) → short gaps. App: upright cameras (ar<1.2) pair with the next camera / span 2 rows (2.2.8–2.2.9), unused while no camera is upright.
- Pictures are drawn at the camera's real shape (trueAr: doorbell 0.75, detect ar if <1.2 or 1.7–2.6, else 16:9) via .vfit (container-type:size, --R, cover/vcon), because 704x480/640x480 sub streams and snapshots are the 16:9 picture squeezed; that made pictures jump between snapshot, sub and HD. Crop positions are --px (0 left … 1 right): Front Door phone List .6 (.cam.fdoor.slim), phone Grid beside Doorbell .8 (.pairrow), wide screens .7; Right Yard Front/Back beside Doorbell 1. When she asks where Front Door sits, list all of these.
- FIXED, DO NOT CHANGE (she confirmed 2026-10-04 21:23): notification clips. HA sends the picture at once, then the GIF/video at alert start + 3 s with URL /wait/<cam>/<start>/<start+3>/clip.gif (keep "+ 3" in the delay and both URLs). clipwait waits up to 22 s for Frigate's recording to cover the asked seconds, then passes Frigate's own clip.mp4 for start..start+3 untrimmed: Frigate starts it on the full picture before the alert, so it moves from the first frame and runs ~5 s+. Only if Frigate fails: retry once with start-1..start+6, then (last resort) 3 s from the live stream. Tried and reverted the same night: shorter wait + live fallback (gave a later, 2 s clip), trimming the GIF to exactly 3 s, delaying to + 15 (slow). Any related change must keep this behaviour.
- 2026-10-04 21:30: adding "-flags -output_corrupt" to nest_doorbell input_args made the Doorbell show no picture at all (Nest's stream starts corrupt, so every frame was dropped); reverted. Do not try it again; the occasional green smear after a Nest stream renewal stays for now.
- 2026-10-04 Samsung video vanishing: the Samsung "· Video" message used the same tag as the picture, so whenever the video couldn't be loaded the picture was gone too. Now (Camera Notifications, Camera Sound Notify, Camera Cat Poop Spot Closet) the Samsung gets the video as its own silent notification (tag <ntag>-v…, channel "Camera Video", importance low) under the picture; the iPhone keeps the same-tag GIF flow (fixed rule unchanged). clipwait now makes each /wait clip once, keeps it 10 min, answers repeats and Range requests at once, and logs every /wait request (`docker logs clipwait`).
