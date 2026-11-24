# Kudos standalone app specification

## 1. Purpose and status

The Kudos app lets colleagues recognize one another with short appreciation messages and makes recent recognition visible in a shared employee feed. This specification combines the approved requirements and technical design and records the implementation plan.

The current app is a **local demo simulation**. It uses seeded demo accounts and local demo sign-in. It is not production authentication and must not be exposed as a shared service. Real organization SSO and user-directory integration are future work.

The implementation currently lives separately in the `kudos/` directory. This specification does not authorize or describe any changes to the existing data-processing files.

## 2. Users and user stories

- **Employee/sender:** an authenticated, active colleague who can submit kudos.
- **Recipient:** an active colleague selected by the sender.
- **Feed viewer:** any authenticated employee; feed access is not limited to senders or recipients.
- **Administrator:** an authenticated user authorized to moderate kudos.

User stories:

- As a colleague, I want to give another colleague kudos with a short appreciation message so that I can recognize their work.
- As a colleague, I want to see recently submitted kudos on the dashboard so that recognition is visible to the team.
- As an administrator, I want to hide or delete inappropriate kudos messages so that the employee feed remains appropriate.

## 3. Functional requirements

1. Employees can choose an active colleague from a searchable/selectable recipient list and submit a required plain-text message.
2. Self-kudos are not allowed. The sender is derived from the signed-in session and cannot be supplied by the form.
3. Messages are limited to 500 characters. Blank or over-limit messages and unknown, inactive, or self recipients are rejected server-side with useful feedback.
4. A successful submission is stored with its sender, recipient, message, and UTC submission time.
5. The dashboard displays visible kudos newest first, showing sender, recipient, message, and date/time. All authenticated employees can see every visible entry.
6. The employee feed displays 20 entries per page; older visible entries are reachable through pagination.
7. Administrators can hide or permanently delete kudos. Hiding retains the record and sets it invisible; deletion removes the record.
8. Only administrators can perform moderation actions. Hidden kudos do not appear in the employee feed.
9. User-provided messages render as escaped text, not executable HTML.
10. The interface supports keyboard use and narrow screens.

Initial scope excludes comments, reactions, and sender/recipient editing. Hidden-message restoration, retention, and export policies remain decisions for review.

## 4. Local demo identity and accounts

The standalone simulation seeds four local accounts:

- Alex Rivera (`alex`)
- Jordan Lee (`jordan`)
- Casey Morgan (`casey`)
- Demo Administrator (`admin`)

The local account picker is a development convenience, not secure authentication. It is restricted to local testing and the app refuses to start when `KUDOS_ENV` is not `local`. Do not expose the demo account selector or app to a shared network.

**Real organization SSO/OIDC and user-directory synchronization are future work.** A future deployment must replace demo sign-in and map administrator permission from a trusted organization role or group.

## 5. Technical design

### Stack and structure

- Python 3.10 or newer
- Flask routes and Jinja templates
- Flask-SQLAlchemy / SQLAlchemy for persistence
- Flask-WTF CSRF protection
- Flask-Migrate / Alembic for database migrations
- SQLite for the local simulation; PostgreSQL is the proposed choice for a future shared deployment

### Data model

**User**

- `id`: local primary key
- `username`, `display_name`, `email`
- `is_active`: controls whether the user can send or receive kudos
- `is_admin`: controls moderation authorization

**Kudos**

- `id`: primary key
- `sender_user_id`, `recipient_user_id`: foreign keys to `User`
- `message`: non-empty plain text, maximum 500 characters
- `created_at`: timezone-aware UTC timestamp
- `is_visible`: non-null boolean, default `true`

An index on `(created_at, id)` supports feed ordering. Feed queries filter to `is_visible == true`, sort by `created_at` and `id` descending, and paginate 20 entries at a time. The moderation view includes visible and hidden records.

### Request flows

**Local demo sign-in:** the user selects a seeded account on `/demo/login`; the selected active user ID is stored in the signed session. Inactive users are signed out. The session identity is the sender identity for submissions.

**Submit kudos:** an authenticated user opens `/kudos/new`, searches/selects an active colleague other than themselves, and submits a message. The server verifies CSRF, validates all values, stores the record, then redirects to the dashboard with a confirmation.

**View feed:** an authenticated user opens `/`. The server retrieves only visible entries, joins sender and recipient display names, and presents the newest entries with pagination.

**Moderate kudos:** an administrator opens `/admin/kudos`. Each hide/delete request checks the administrator role server-side and verifies CSRF. Hiding sets `is_visible` to `false`; deleting permanently removes the record. Non-administrators receive a forbidden response. Restoring hidden entries is not currently specified.

### Routes

- `GET /demo/login`, `POST /demo/login`: local-only demo account selection
- `POST /logout`: end the current demo session
- `GET /`: authenticated employee feed
- `GET /kudos/new`, `POST /kudos/new`: authenticated submission form and handler
- `GET /admin/kudos`: administrator moderation list
- `POST /admin/kudos/<id>/hide`: hide a kudos
- `POST /admin/kudos/<id>/delete`: permanently delete a kudos

## 6. Security and privacy

- Demo sign-in is for local simulation only; organization authentication is not implemented.
- Enforce administrator authorization server-side on every moderation route, not only in the UI.
- Derive the sender from the session; validate active recipient, self-kudos, and message length on the server.
- Protect form submissions with CSRF tokens.
- Use ORM parameterized queries, foreign keys, and template escaping.
- Do not log message contents or unnecessary personal data.
- The shared employee feed intentionally includes all visible kudos. Confirm organization policy before any future shared deployment.

## 7. Spam, inappropriate content, and moderation tracking

### Current local demo

- **Spam:** There is no rate limiting or spam detection. Demo users can be selected locally; server-side validation and CSRF protection are not spam controls.
- **Duplicate submissions:** There is no deduplication or idempotency key. Each valid POST creates a new kudos, so repeated submissions can create duplicates. A successful POST redirects to the feed, which avoids a browser refresh resubmitting the form in the normal flow.
- **Inappropriate content:** Messages are plain text and safely escaped when displayed, but the app does not automatically detect or filter inappropriate content. An administrator can manually hide or permanently delete an entry.
- **Moderation tracking:** The app stores the current `is_visible` state, but it does not persist who hid or deleted an entry, when moderation occurred, or why. Permanent deletion leaves no moderation history.

### Possible future improvements

- Add per-account submission limits and abuse monitoring after real SSO identifies users reliably.
- Add an idempotency mechanism or duplicate-submission warning for retry/double-submit cases.
- Consider a report/flag workflow or moderation queue; any automated content screening should supplement, not silently replace, administrator review.
- Add a moderation audit record containing administrator, action, timestamp, and optional reason. Decide how audit history should relate to permanently deleted messages while minimizing retained personal content.

## 8. Implementation plan and status

| Task | Status |
| --- | --- |
| Create a standalone Flask project, dependency manifest, templates, styles, and local run instructions | Complete |
| Define the user/kudos schema and create the initial Alembic migration | Complete |
| Add seeded demo employees and a demo administrator with local-only sign-in | Complete |
| Implement recipient search, server-side submission validation, and confirmation/error feedback | Complete |
| Implement the visible-only, newest-first employee feed and 20-entry pagination | Complete |
| Implement administrator-only hide and permanent-delete actions | Complete |
| Add automated tests for submissions, validation, feed visibility/order/pagination, moderation, CSRF, and demo-mode restrictions | Complete |
| Replace demo sign-in with organization SSO/OIDC and synchronize the employee directory | Future work |
| Prepare a shared deployment with PostgreSQL, production hosting/security settings, backups, and policy approval | Future work |

## 9. Testing strategy and current results

The feature tests use Python `unittest` and an in-memory SQLite database. They cover:

- Seeded employee/admin accounts and local-only mode
- Login and recipient-selector rendering
- Valid submissions and rejection of blank, over-limit, self, inactive, and unknown recipients
- Shared visibility, hidden-entry exclusion, newest-first order, and pagination boundaries
- HTML escaping
- Admin hide/delete permissions and denial for non-administrators
- CSRF rejection when a form token is missing

Run the feature tests from `kudos/`:

```sh
python -m unittest discover -s tests -v
```

The feature suite has 13 passing tests at the time this specification was written. The existing root-level data-processing regression suite was also run separately and passed; it is not part of the Kudos app.

The initial migration and demo-user seed command were verified against a temporary SQLite database.

## 10. Local start and use

From `kudos/`:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
.venv/bin/python -m flask --app app db upgrade
.venv/bin/python -m flask --app app seed-demo-users
.venv/bin/python -m flask --app app run --host 127.0.0.1
```

Open <http://127.0.0.1:5000>, choose a demo account, and submit kudos or browse the feed. Sign in as **Demo Administrator** to open Moderation and hide or permanently delete an entry. The local SQLite database is stored at `instance/kudos.sqlite3`.

## 11. Deployment considerations and future work

The Flask development server, demo account picker, and local SQLite setup are for local testing only. Do not expose them on a shared or production network.

Before any shared deployment:

1. Integrate organization SSO/OIDC and the authoritative active-user directory; remove or disable demo account selection.
2. Map administrator permissions from a trusted identity-provider group or equivalent server-managed role.
3. Use PostgreSQL, apply migrations during deployment, and configure backups and recovery.
4. Use a production WSGI server over HTTPS; configure secure session cookies, secrets, and environment-specific settings.
5. Confirm feed visibility, retention/export, deletion, and hidden-entry restoration policies with the organization.
6. Add operational health checks and structured error logging without storing kudos message contents in logs.

Future decisions still open include the SSO provider/directory source, whether hidden entries can be restored, and retention/export policy.
