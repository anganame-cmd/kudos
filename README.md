# Kudos local simulation

This is a standalone Flask simulation. It uses seeded demo accounts and local demo sign-in; it is **not production authentication** and must not be exposed as a shared or production app. Real organization SSO is a future integration.

## Requirements

- Python 3.10 or newer
- Dependencies from `requirements.txt`

## Start locally

From the `kudos/` directory:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
.venv/bin/python -m flask --app app db upgrade
.venv/bin/python -m flask --app app seed-demo-users
.venv/bin/python -m flask --app app run --host 127.0.0.1
```

Open <http://127.0.0.1:5000>. The SQLite database is stored at `instance/kudos.sqlite3`.

The demo account picker includes:

- Alex Rivera
- Jordan Lee
- Casey Morgan
- Demo Administrator

Sign in as any colleague to submit kudos and view the shared feed. Sign in as **Demo Administrator** to hide or permanently delete entries from the Moderation page. Hidden entries remain stored but do not appear in the employee feed.

## Run tests

```sh
python -m unittest discover -s tests -v
```

Tests use an in-memory SQLite database and do not write to the local simulation database.

## Local-only safety

The app binds to `127.0.0.1` by default and refuses to start if `KUDOS_ENV` is not `local`. Do not change this guard or expose the demo account selector outside local testing. Before any shared deployment, replace demo sign-in with organization SSO and review the deployment/security design.
