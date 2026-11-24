# Kudos feature: initial requirements

## Purpose

Let colleagues recognize one another with short appreciation messages and make recent recognition visible on the internal dashboard.

## Users

- **Sender:** an authenticated, active colleague who submits a kudos.
- **Recipient:** an authenticated, active colleague selected by the sender.
- **Feed viewer:** an authenticated colleague who can read the shared kudos feed.
- **Administrator:** an authenticated user with the administrator permission who can moderate kudos.

## User stories

- As a colleague, I want to give another colleague kudos with a short appreciation message so that I can recognize their work.
- As a colleague, I want to see recently submitted kudos on the dashboard so that recognition is visible to the team.
- As an administrator, I want to hide or delete inappropriate kudos messages so that the employee feed remains appropriate.

## Functional requirements

1. A sender can open a form to give kudos.
2. The form provides a searchable/selectable list of active colleagues.
3. The sender can enter a required, plain-text appreciation message.
4. The sender can submit the kudos and receive clear confirmation or validation feedback.
5. A successful submission is stored with its sender, recipient, message, and submission time.
6. The main dashboard shows a feed of recently submitted kudos, newest first. Each item shows the sender, recipient, message, and date/time.
7. All authenticated employees can view every visible kudos entry in the shared feed. Older visible entries remain accessible through pagination.
8. Invalid or inactive recipients, blank messages, and messages over the configured length are rejected server-side.
9. Administrators can hide or delete inappropriate kudos. Hiding retains the record but removes it from the employee feed; deleting permanently removes the record.
10. Only administrators can perform moderation actions.

## Initial product assumptions for review

- Self-kudos are not allowed.
- Messages are plain text and limited to 500 characters.
- Any authenticated employee can see every visible kudos entry; feed visibility is not restricted to the sender or recipient.
- The initial release has no comments, reactions, or sender/recipient editing. Administrator moderation is included.
- Feed pagination starts with 20 entries per page; entries are retained unless a later retention policy is agreed.
- The standalone local simulation uses seeded demo users, including a demo administrator, for testing.
- Local demo sign-in is only for the standalone simulation. Real organization SSO and user-directory integration are future work.

These are proposed defaults, not confirmed policy decisions.

## Acceptance criteria

- An authenticated demo sender can select another active demo colleague, enter a valid message, submit, and see the resulting kudos in the feed.
- A newly submitted entry appears ahead of older entries and identifies both sender and recipient.
- Feed pagination can reach entries beyond the first page without duplicating or skipping entries during ordinary navigation.
- Blank, over-limit, self-directed, inactive-recipient, and unknown-recipient submissions do not create records and produce useful validation feedback.
- All authenticated employees can view every visible kudos entry; hidden entries do not appear in the employee feed.
- Unauthenticated users cannot create kudos or access the feed.
- Only administrators can hide or delete kudos; non-administrators cannot perform moderation actions.
- Hidden kudos no longer appear in the employee feed.
- User-provided text is displayed as text, not interpreted as HTML.
- The interface is usable on narrow screens and with keyboard navigation.

## Open questions

1. For a future integration, which SSO/OIDC provider and user-directory source should deployment use?
2. Should users be allowed to give themselves kudos?
3. Is a 500-character limit appropriate?
4. Should hidden kudos be restorable by an administrator?
5. Is there a retention or export policy for kudos history?
