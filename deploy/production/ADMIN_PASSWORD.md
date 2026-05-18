# Admin password setup

Production uses app-level admin login. Store only a password hash in `deploy/production/.env`; do not store the plain password.

## Generate password hash

Run this from the repository root:

```bash
uv run python -c 'from getpass import getpass; from app.auth import hash_admin_password; print(hash_admin_password(getpass("Admin password: ")))'
```

Type the admin password when prompted. The password input is hidden. Copy the printed `pbkdf2_sha256:...` hash.

## Set production env values

Edit `deploy/production/.env` on the server:

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=<paste-generated-hash-here>
APP_SECRET=<long-random-secret>
```

`APP_SECRET` signs the session cookie. Changing it logs out existing admin sessions.

## Apply the change

Restart the app service after changing `.env`:

```bash
docker compose \
  --env-file deploy/production/.env \
  -f deploy/production/compose.production.yml \
  up -d app nginx
```

Then open `/login` and sign in with `ADMIN_USERNAME` and the plain password used to generate the hash.
