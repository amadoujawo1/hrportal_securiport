# Copilot instructions for HRPortal

This project is a small Flask monolith (web UI + API + realtime) using SQLAlchemy and Flask-Migrate.
Keep instructions precise and anchored to files that show the real behavior.

**Big Picture:**
- `main.py`: Primary application entrypoint — defines Flask app, SocketIO, routes, and runs via `socketio.run(app, host='0.0.0.0', port=5009, debug=True)`.
- `models.py`: SQLAlchemy ORM models (`User`, `Leave`, `Document`, `Notification`) and simple helper methods.
- `database.py`: `db = SQLAlchemy()` instance used across the app.
- `utils.py`: helper functions for file uploads, email sending, and a `requires_admin` decorator used across views.
- `migrations/` + `alembic.ini`: project uses Flask-Migrate/Alembic for schema migrations.

**Key behaviours & data flows to remember:**
- HTTP routes (in `main.py`) read form data, create ORM objects (`models.py`) and call `db.session.commit()`.
- Realtime notifications are emitted via `flask_socketio.SocketIO` (`socketio.emit(..., room=str(user_id))`).
- File uploads use `utils.save_document()` and are saved under `static/uploads` by default.
- Email sending is implemented in `utils.send_email()` but is guarded by environment variables; code sometimes logs and silently skips if SMTP not configured.

**Developer workflows & commands (discoverable from repo):**
- Install deps: `pip install -r requirements.txt` — note `requirements.txt` is minimal; additional runtime dependencies used in code include `Flask-SocketIO`, `reportlab`, and a MySQL driver (`pymysql` or `mysqlclient`). Verify and add them to `requirements.txt` before running.
- Run the app locally: `python main.py` (starts SocketIO server on port `5009`).
- Initialize DB (one-off): `python init_db.py` creates the `hrportal` MySQL database (credentials are hardcoded in that script).
- Migrations: the project has `migrations/` (Alembic). Use `flask db migrate` / `flask db upgrade` when you add models — the app uses `Flask-Migrate` in `main.py`.
- Tests: there is a `tests/` folder and a couple of test files (`test_notifications.py`, `test_admin_login.py`). Run tests with `pytest` from repo root.

**Project-specific conventions & gotchas:**
- Configuration is mostly inlined in `main.py` (e.g., `SQLALCHEMY_DATABASE_URI` and `SECRET_KEY` are set there). Search `main.py` before assuming config comes from environment.
- Passwords are stored and compared as plaintext in `models.py` / `main.py` — this is how the code currently works (do not change login logic without adding hashing and updating tests).
- There are two `requires_admin` implementations (one in `utils.py` and another in `main.py`). Prefer `utils.requires_admin` when adding new admin-restricted endpoints to avoid duplication.
- File upload handling centralised in `utils.save_document()`; uploaded filenames are prefixed with `{user_id}_{timestamp}_` and written to `static/uploads`.
- The code sometimes performs DB schema patches at runtime (e.g., `init_database()` in `main.py` attempts to ALTER `user` to add `job_title` if missing). Be careful when refactoring that logic.

**Integration points & external dependencies to check before changes:**
- MySQL: connection strings appear in `main.py` and `init_db.py` with different credentials — verify which environment/credentials are correct for the target deployment.
- SMTP: `utils.send_email()` reads SMTP configuration from environment variables (see function docstring). If email behavior is expected, ensure `SMTP_HOST`, `SMTP_PORT`, etc. are set.
- Realtime: SocketIO rooms use stringified user id (e.g., `room=str(user_id)`). Keep that string-room convention when emitting/listening.

**When making changes, follow these concrete examples:**
- Adding a new route that writes DB rows: mirror pattern in `apply_leave` — validate inputs, create ORM object, `db.session.add(...)`, `db.session.commit()`, and wrap commit in try/except with `db.session.rollback()` on error.
- Adding file uploads: call `allowed_file()` and `save_document()` from `utils.py` (examples in `apply_leave` and `upload_leave_document`).
- Emitting notifications: use `socketio.emit('notification', {...}, room=str(user_id))` so front-end listeners already in place will receive events.

If anything in these instructions is unclear or you want more details (for example, specific tests to look at or missing requirements), tell me which area to expand and I'll iterate.
