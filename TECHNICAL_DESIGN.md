# Kudos feature: initial technical design

## Proposed stack

- **Flask** for a small server-rendered web application.
- **Jinja** templates for the submission form and dashboard feed.
- **SQLAlchemy** for database access and model definitions.
- **SQLite** for local development; **PostgreSQL** for a shared or production deployment.
- **Alembic/Flask-Migrate** for schema migrations.
- Seeded local demo identities for the standalone simulation, including a demo administrator.
- Real organization SSO through OIDC and user-directory synchronization are future integrations, not part of the standalone simulation.

This is a proposal for review, not an implementation. The project will live under `kudos/`, separate from the existing data-processing files. The local demo sign-in must be restricted to local testing and disabled in any shared or production deployment.

## Main components

1. **Local demo authentication:** lets a tester select one of the seeded demo accounts; it is not production authentication.
2. **Future authentication integration:** validates the user's organization SSO identity and resolves it to an active application user.
3. **User directory adapter:** supplies active colleague IDs and display names for recipient selection from seeded demo users locally, with an organization directory integration in future deployments.
4. **Kudos service:** validates a submission, stores it, and retrieves feed entries.
5. **Web routes and templates:** render the dashboard feed and handle the create-kudos form.
6. **Relational database:** stores users and kudos with foreign-key relationships.

## Data model

### `User`

- `id`: primary key; use a local ID for seeded demo users, with a future mapping to a stable identity-provider subject.
- `display_name`: name shown in the selector and feed.
- `email`: organization email, if available and needed for identity matching.
- `is_active`: whether the user may send or receive kudos.
- `is_admin`: whether the user may moderate kudos; set on the seeded demo administrator locally and mapped from a trusted administrator role or SSO group in a future integration.

### `Kudos`

- `id`: primary key.
- `sender_user_id`: foreign key to `User.id`.
- `recipient_user_id`: foreign key to `User.id`.
- `message`: non-empty plain text, maximum 500 characters under the proposed default.
- `created_at`: timezone-aware UTC timestamp.
- `is_visible`: non-null boolean, default `true`; set to `false` when an administrator hides the kudos.

Add a database index on `(created_at, id)` to support newest-first feed retrieval. Use a migration for schema changes. The user table may be synchronized from the organization directory rather than treated as the authoritative employee directory.

## Request flows

### Give kudos

1. A signed-in demo user opens the form.
2. The server loads active recipients (excluding the sender under the proposed default).
3. On submission, the server verifies the CSRF token and validates the message and recipient against current server-side data.
4. The server inserts a `Kudos` row and commits the transaction.
5. On success, redirect to the dashboard and show a confirmation. On validation failure, re-render the form with actionable errors.

### View feed

1. A signed-in demo user opens the dashboard.
2. The server queries only kudos with `is_visible == true`, newest-first, joining sender and recipient display names.
3. Return 20 visible entries by default and provide pagination for older visible entries. A cursor based on `(created_at, id)` is preferred if entries are added frequently; offset pagination is acceptable for a small initial dataset.
4. Render messages with normal template escaping.

### Moderate kudos

1. An administrator opens the moderation view, which can include both visible and hidden records.
2. The server checks the authenticated user's administrator permission for every moderation request; hiding controls in the UI are not an authorization boundary.
3. Hiding sets `is_visible` to `false`. The record remains stored but is excluded from all employee feed queries.
4. Deleting permanently removes the kudos record. The action is available only to an administrator and requires CSRF protection.
5. A hidden record's restoration behavior is not specified yet; confirm whether administrators need an unhide action.

## Initial route outline

- `GET /`: authenticated dashboard with the recent kudos feed.
- `GET /kudos/new`: authenticated submission form and active recipient options.
- `POST /kudos`: authenticated submission endpoint; validates and stores a kudos, then redirects.
- `GET /demo/login` and `POST /demo/login`: local-only demo account selection; disabled outside local testing.
- `GET /admin/kudos`: administrator-only moderation view.
- `POST /admin/kudos/<id>/hide`: administrator-only action that hides a kudos.
- `POST /admin/kudos/<id>/delete`: administrator-only action that permanently deletes a kudos.

Use the framework's normal HTML form and redirect flow first; a separate JSON API is unnecessary unless another client is planned.

## Security and privacy

- Require a signed-in local demo account for the dashboard, feed, and submission in the standalone simulation; integrate organization authentication only in a future deployment.
- Do not expose the demo account selector or demo identity mechanism in a shared or production deployment.
- Require the administrator permission on every moderation route and enforce it server-side.
- Derive the sender from the authenticated session; never accept a sender ID from the form.
- Enforce recipient validity, active status, self-kudos policy, and message length on the server.
- Use CSRF protection for form submissions.
- Render messages as escaped plain text; do not mark user content safe or allow arbitrary HTML.
- Use SQLAlchemy parameterized queries and database constraints for relationships.
- Avoid logging message contents or other unnecessary personal data.
- Every authenticated employee can view every kudos entry where `is_visible == true`; hidden entries are excluded from the employee feed.

## Testing plan

- Unit tests for valid submission and each validation failure.
- Route tests for demo authentication requirements, successful redirect/confirmation, and form errors.
- Feed tests for newest-first ordering, pagination boundaries, sender/recipient labels, and exclusion of hidden messages.
- Moderation tests proving administrators can hide/delete, hidden messages disappear from the employee feed, and non-administrators are denied.
- Security-oriented tests that submitted HTML is rendered escaped and that invalid user IDs cannot be submitted.
- Integration test against the deployment database engine before production release.

## Deployment and operations

- Use seeded demo accounts and SQLite for local simulation. Real SSO settings and user-directory synchronization are future integration work.
- Use PostgreSQL and migrations for shared deployments; do not rely on a local SQLite file for multiple production instances.
- Add health checks and structured error logging without recording kudos message contents.
- Define backup, retention, and employee offboarding behavior before production.

## Decisions needed before implementation

- Select the future SSO provider and source of the organization user directory.
- Confirm feed visibility, self-kudos, message length, sender/recipient editing, hidden-message restoration, and retention policies.
- Confirm the deployment environment and whether PostgreSQL is available.
