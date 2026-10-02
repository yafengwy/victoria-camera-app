# Victoria's Home

Camera app for the home Frigate server (mini PC, `~/frigate`).

- `index.html` — the app. The mini PC copies it from this repo into `~/frigate/app/` every minute, so a push here goes live within a few minutes.
- `app-nginx.conf` — web server config for the app container (serves the app, forwards `/api/` to Frigate).
