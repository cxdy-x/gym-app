# Gym Log

A small, phone-friendly workout logger for a private home network. It provides a one-tap current workout, fast entry of sets/reps/weight, and a searchable-in-place history. There is no cloud account, telemetry, or external database.

## Behaviour

The initial four-workout rotation is Upper Push → Lower Body → Upper Pull → Full Body. The app creates only one pending workout. It **does not use calendar dates to advance the plan**: if a session is missed, the same session is still shown next time. Completing it writes the log and creates the next item in the rotation.

The database is seeded once with the two sessions supplied in the original conversation. Their dates are marked `Imported from chat`, because no dates were provided.

## Run on the home server

1. Install Docker Engine and Docker Compose on `10.0.0.10`.
2. Clone this private repository to a convenient directory on the server.
3. Create persistent storage and give the container user access:

   ```sh
   sudo mkdir -p /mnt/gym-app/images
   sudo chown -R 10001:10001 /mnt/gym-app
   ```

4. From the repository directory, build and start it:

   ```sh
   docker compose up -d --build
   ```

5. On the iPhone, open `http://10.0.0.10:2222` in Safari and use Share → Add to Home Screen.

The bind mount means the SQLite database (`/mnt/gym-app/gym.db`) and image directory remain intact when the container is rebuilt or replaced. The Compose configuration binds host port `2222` to the app’s internal port `8000`.

## Updates and backup

```sh
git pull
docker compose up -d --build
```

The workout rotation lives in `routine.json`, not in code, so you can hand-edit
weights/reps any time — or see `WEEKLY_PROMPT.md` for a no-cost way to refresh
it weekly using a free chat LLM and your logged history, no API key needed.

Back up `/mnt/gym-app/gym.db` while the service is stopped, or use SQLite's online backup mechanism. The database is the only essential persistent app data.

## Security note

This is intentionally a no-login app for a trusted LAN. Do not forward port 2222 to the public internet. If remote access is needed, put it behind a VPN (such as Tailscale/WireGuard) or an authenticated reverse proxy, set a random `SECRET_KEY`, and use HTTPS.

## Local development

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Visit `http://localhost:8000`. Set `GYM_DATA_DIR` to choose a different local data folder.
