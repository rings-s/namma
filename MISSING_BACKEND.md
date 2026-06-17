# Missing / Insufficient Backend for the Frontend

Tracked as the SvelteKit frontend is built module-by-module. Each entry is a
real gap found against the existing DRF API — no fake fields were invented to
work around them. Resolve on the backend, then remove the entry.

## App Shell & Auth (`g_shell`)

### 1. ✅ RESOLVED — per-request organization scoping on list endpoints
`TenantScopedQuerysetMixin.get_queryset` now honors `?organization=<id>`,
narrowing within the user's tenant scope (never widening). Below is the
original report.


`core.api.TenantScopedViewSet` filters querysets by the user's `UserRole`
membership across **all** their organizations, and the only filter backends
enabled are `SearchFilter`/`OrderingFilter` (no `DjangoFilterBackend`, no
`?organization=` param). The org switcher is therefore client-side state and
lists (e.g. dashboard `daily-metrics`, `goals`) are filtered to the current org
**in the browser**.
- **Impact:** over-fetching for users in many orgs; can't paginate per-org.
- **Asked for:** a documented `?organization=<id>` query param (or an
  `X-Organization` header) honored by `TenantScopedQuerysetMixin`.

### 2. ✅ RESOLVED — `/me/` now reports two-factor status
`UserSerializer` exposes a read-only `two_factor_enabled` (true once the TOTP
device is confirmed). Below is the original report.


`UserSerializer` exposes no `two_factor_enabled` flag, and there is no GET
endpoint for `accounts.TwoFactorDevice`. The Security page therefore can't show
whether 2FA is currently on; it offers both enable and disable flows and relies
on `POST /auth/2fa/setup/` returning 400 ("already enabled") to detect state.
- **Asked for:** add `two_factor_enabled` (read-only) to `/me/`, or a
  `GET /auth/2fa/` status endpoint.

### 3. `/auth/sessions/` can't identify the current session
`UserSessionSerializer` excludes `refresh_jti` (correct — it's a credential),
but nothing tells the client which session is the device it's signed in on, so
the "This device" marker can't be rendered.
- **Asked for:** a boolean `is_current` on the session serializer, computed from
  the access token's refresh lineage.

## Customer Lifecycle Engine (Prompt 2)

### 4. ⚠️ PARTIALLY RESOLVED — UserRole now embeds user identity
`UserRoleSerializer` now embeds a read-only `user_detail` (id, full_name,
email), so the assign picker can show names. The Conversation serializers
(customer/assigned_to display names) are **not** yet nested and there is still
no `GET /users/` endpoint — see below.


`ConversationSerializer` (and `ConversationMessageSerializer`) expose
`customer`, `assigned_to`, `branch` as bare ids, and `UserRoleSerializer` is
`__all__` with no embedded user object — and there is **no list-users endpoint**
in `accounts` (only `/me/` and `/user-roles/`). So the inbox can't show the
assignee's name and the Assign picker can only offer raw user IDs from
`/user-roles/` filtered to the org.
- **Impact:** the inbox resolves *customer* names client-side by cross-loading
  `/customers/`, but staff/assignee names are unresolvable; the assign dialog
  takes a user UUID.
- **Asked for:** either nest `customer`/`assigned_to` (id + display name) on the
  conversation serializer, or add a `GET /users/?organization=` (org staff)
  endpoint, or embed `user` (id, full name, email) on `UserRoleSerializer`.

### 5. Conversation reply and outbound dispatch are not coordinated
A reply is `POST /conversation-messages/ {conversation, direction:"outbound",
body}` — `sender_user`, `dispatch`, `read_at` are read-only and the view only
stamps `last_message_at`. The actual SMS/email send is a **separate** pipeline:
create a `MessageDispatch` then `POST /message-dispatches/{id}/send/`. There is
no endpoint that records the thread message *and* sends it atomically.
- **Impact:** the UI records replies in the thread but cannot itself deliver
  them; agents would have to dispatch separately. The reply box shows a notice.
- **Asked for:** a `POST /conversations/{id}/reply/` that creates the outbound
  message, builds the dispatch, enqueues `send`, and links them.

### 6. Clinical note content is encrypted and not readable via the API
`ClinicalNote.content_encrypted` is exposed raw by a `__all__` serializer with no
decrypted accessor, and `export_customer_data` deliberately omits note content
("released through the clinical access flow, not the bulk export"). The viewset
also accepts writes to `content_encrypted` but does **not** encrypt on write.
- **Impact:** the 360 Clinical Notes tab shows metadata only (type, sensitivity,
  author, date) with an explanatory notice; no read/edit of note body. No
  client-side decryption is attempted.
- **Asked for:** a decrypted `content` (read) + plaintext-in/encrypt-on-write
  field on the serializer behind the clinical-access role, plus access logging.

### 7. `CustomerDocument.file_url_encrypted` is opaque
Same shape as #6 — the document's storage URL is encrypted with no decrypted
accessor, so the 360 Documents tab can list metadata (`document_type`,
`is_sensitive`, `uploaded_by`, date) but cannot link to or preview the file.
- **Asked for:** a signed, decrypted `download_url` action behind the role gate.

## Not yet built (no frontend attempted — endpoints exist, deferred to later modules)
- Notifications inbox, global cross-entity search — part of `g_shell` per the
  build prompt but deferred until after the core auth shell is verified.
- Promotions, NotificationTemplates, MessageTemplates approval UI — endpoints
  exist; surfaced incidentally (journey step templates) but no dedicated module
  built yet.
