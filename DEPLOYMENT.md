# Deployment reference

## Network

`compose.yaml` publishes the service as `10.0.0.10:2222`:

| Host | Port | Container port | Purpose |
|---|---:|---:|---|
| `10.0.0.10` | `2222` | `8000` | Gym Log web interface |

If the server firewall is enabled, allow TCP port 2222 from the home LAN only. Example for UFW: `sudo ufw allow from 10.0.0.0/24 to any port 2222 proto tcp`.

## Persistent files

| Server path | Container path | Contents |
|---|---|---|
| `/mnt/gym-app` | `/data` | SQLite database and future image assets |

Never delete `/mnt/gym-app` during a deployment. A plain `docker compose down` is safe because the data is a bind mount, not a Docker volume.

## Health checks

After deploying, visit `http://10.0.0.10:2222`. To check service logs, use `docker compose logs --tail=100 gym-app` from the repository directory.

## Recovery

To restore a backup, stop the container, replace `/mnt/gym-app/gym.db` with the backup, ensure it is owned by UID/GID `10001`, and start the container again. The app's initialization is idempotent: it will not add the imported history again when the database already contains migration version 1.
