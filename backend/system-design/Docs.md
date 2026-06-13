# نماء | NAMAA
## The Operating System for Service Commerce in the Gulf
### Master Business & Platform Documentation — Investor & Partner Edition (v2.1, June 2026)
>  **One line:** Namaa is the compliance-native, AI-driven operating system that runs every revenue-generating minute of a Gulf service business — bookings, POS, payments, staff, marketing, and ZATCA e-invoicing — in one Arabic-first platform. 

>  **What changed in v2.1:** Every technical claim in this document is now grounded in the canonical data model (`namaa-models.eraser` — **123 entities across 13 domains** with a fully mapped relationship graph). §5 (Feature Catalog) cross-references the exact entities behind each capability; §6 (Architecture) has been rewritten around the model's domain map, state machines, and decision flows; Appendix A carries the full entity-to-domain index. 

---

# 1. Executive Summary
Service businesses are the fastest-growing commercial segment of Saudi Arabia's Vision 2030 economy — clinics, salons, spas, fitness studios, and the entertainment venues created by an unprecedented national push into leisure and tourism. Yet the average multi-branch operator in Riyadh still runs the business on a patchwork of seven disconnected tools: a booking app, a cashier program, WhatsApp on a personal phone, Excel for commissions, a separate ZATCA invoicing utility, paper consent forms, and gut feeling for marketing.

**Namaa replaces all of it.** One platform, built in Saudi Arabia for the Gulf, that unifies multi-branch operations, intelligent CRM, automated omnichannel engagement, real-time POS with regional payments, and Phase-2 ZATCA e-invoicing — with an AI layer that turns daily operational data into revenue decisions.

Our wedge is unique in this market: **compliance is the Trojan horse, payments are the engine, AI is the moat.** Every Saudi service business is legally compelled toward Phase-2 e-invoicing; Namaa makes compliance a one-click property of normal selling rather than a separate burden. Once we run the invoice, we run the payment — earning a platform margin on every card transaction. And because we see bookings, payments, inventory, and engagement in one schema — a single 123-entity relational model per tenant — our AI predictions (churn, demand, staffing) work out of the box in ways point-solutions structurally cannot match.

**The business model** combines high-retention SaaS subscriptions (449 → 3,500+ SAR/month across four tiers) with usage-based revenue (payments margin, messaging margin, AI add-ons) — a model designed for net revenue retention above 110% as customers open branches and adopt modules.

**We are raising seed funding** to complete the platform build, achieve ZATCA certification, acquire our first 100 paying customers in Riyadh and Jeddah, and reach a 3.5M+ SAR ARR run rate within 12 months of launch (detailed plan in §9–10).

---

# 2. The Problem
A typical 3-branch clinic or salon group in KSA today:

1. **Loses 25–40% of potential bookings** because booking happens by phone during working hours only, and double-bookings of rooms/devices are prevented by a paper diary.
2. **Suffers chronic no-shows** with no deposit enforcement and manual reminder calls.
3. **Pays staff commissions calculated in Excel** — slow, disputed, and demotivating.
4. **Faces ZATCA Phase-2 enforcement waves** with invoicing tools that don't talk to the cashier screen, risking fines and operational chaos.
5. **Owns zero customer intelligence:** no LTV, no churn signal, no segmentation — marketing is a blast SMS to everyone, in violation of PDPL consent rules they've never heard of.
6. **Cannot see the business in real time:** the owner learns branch performance days later, from a WhatsApp photo of a handwritten summary.
International tools (Fresha, Zenoti, Booker) are English-first, compliance-blind to ZATCA/PDPL, and price in dollars with no local support. Local tools solve one slice (booking _or_ cashier _or_ invoicing) and force the patchwork anyway. **Nobody owns the full operating layer. Namaa does.**

---

# 3. The Market
**Why now — three converging forces:**

- **Regulatory forcing function:** ZATCA's Phase-2 integration waves are progressively compelling every VAT-registered business into certified, cryptographically-stamped e-invoicing. This converts "software is nice to have" into "software is the law."
- **Vision 2030 service-economy boom:** entertainment licensing (GEA), tourism targets, gym/wellness expansion, and clinic privatization are creating tens of thousands of new venues — all born digital-ready, none served by an integrated local platform.
- **Payment digitization:** mada, Apple Pay, and SoftPOS adoption make embedded payments — our highest-margin layer — frictionless to attach.
**Sizing method (bottom-up, internal estimates to be validated against GASTAT/MISA registries during diligence):** KSA alone hosts well over 100,000 VAT-relevant service venues across salons/barbershops, clinics (dental, derma, physio), spas/wellness, fitness, and entertainment. At a blended 1,000–1,400 SAR/month software + payments revenue per venue, the Saudi serviceable market alone exceeds **1.5B SAR annually**, before GCC expansion (UAE e-invoicing arrives next, and our compliance engine transfers directly).

**Beachhead:** multi-chair salons/barbershops and dental/derma clinics in Riyadh and Jeddah — highest density, fastest sales cycles, strongest compliance pain. Entertainment/ticketing follows as the second wave (§10).

---

# 4. The Product — What Makes Namaa Different
Four compounding differentiators, in order of defensibility:

1. **Compliance-native core.** ZATCA Phase 2 (cryptographic stamps, PIH hash chains, ICV counters, device CSID onboarding, clearance & reporting flows) is built into the invoice lifecycle itself — not bolted on: the model carries a dedicated four-entity ZATCA subsystem (`zatca_devices` , `zatca_counters` , `e_invoices` , `e_invoice_submissions` ) chained directly to the fiscal documents (`invoices` , `credit_notes` , `debit_notes` ). PDPL consent management is built into the CRM (`consent_records`  per customer per channel per purpose). This is 12–18 months of regulatory engineering that global competitors will not do and local point-tools cannot generalize.
2. **Embedded payments.** Moyasar-powered acceptance (mada, Visa/Mastercard, Apple Pay) wired directly into POS, deposits, gift cards, and online booking through a two-object payment model (`payment_intents`  → `payments` ) with idempotent webhook processing (`payment_webhook_events` ) and full settlement reconciliation (`settlements` , `settlement_lines` ) — with Namaa earning a platform margin on volume. Software subscriptions get us in the door; payments scale our revenue with the customer's success.
3. **One schema → real AI.** Because bookings, sales, inventory, staff, and messaging live in one data model per tenant — 123 entities, every row tenant-scoped — our AI layer (LTV prediction, churn early-warning, demand forecasting, smart staffing, Arabic marketing-copy generation) trains on complete behavioral pictures: the structural advantage no patchwork can replicate.
4. **Arabic-first, Gulf-first.** True RTL interfaces, bilingual invoices and messaging (polymorphic `translations`  table per tenant), Hijri-aware scheduling, prayer-time and Ramadan operating-hour intelligence modeled at the branch level (`branches.prayer_time_blocking` , `branches.ramadan_hours_override` , `branches.hijri_display_preference` , quiet-hours fields), GCC currencies and timezones, and in-Kingdom data residency options.
---

# 5. Complete Feature Catalog (Consolidated, Model-Mapped)
_Impact figures below are category benchmark outcomes Namaa is engineered to deliver and will be validated with design-partner data; they are targets, not audited results. Each section now lists the_ **_backing entities_** _from the canonical data model._

## 5.1 Organization & Multi-Branch Control
**Backing entities:** `organizations`, `organization_settings`, `branches`, `branch_hours`, `retention_policies`, `countries`, `currencies`, `translations`.

Multi-organization management under one account; branch-specific hours, pricing, services, and staff; industry templates (clinic, salon, spa, fitness, entertainment) via `organizations.industry`; GCC timezones and currencies (SAR, AED, KWD, BHD, OMR, QAR); geo-located branch finder (`branches.latitude/longitude`); consolidated reporting with branch drill-down. The `organizations` entity natively carries the Saudi commercial identity required by ZATCA — `vat_number`, `commercial_registration_number`, and full national-address fields (`street_name`, `building_number`, `district`, `city`, `postal_code`). Branch-level Gulf intelligence is first-class schema, not configuration JSON: `prayer_time_blocking`, `ramadan_hours_override`, `quiet_hours_start/end`, `hijri_display_preference`. _Target impact: ~60% reduction in multi-location administrative overhead._

## 5.2 Staff, Scheduling & Compensation
**Backing entities:** `employees`, `employee_schedules`, `employee_services`, `employee_shifts`, `commission_rules`, `commission_entries`, `payroll_periods`, `employee_cost_components`, `user_roles`.

Rich employee profiles with certifications and documents; branch- and function-scoped RBAC permissions (`user_roles` carries `organization_id` + `branch_id` + `role`); qualification-linked service assignments (`employee_services` — only listed employee×service pairs are bookable); flexible shift templates with breaks, time-off workflows, and holiday exceptions (`employee_schedules` as the recurring pattern, `employee_shifts` as rostered instances). The commission engine resolves `commission_rules` by precedence (employee ▸ service/product ▸ branch ▸ org default; percentage, fixed, or tiered) and posts append-only `commission_entries` in real time on each completed sale — rule parameters are snapshotted per entry so later edits never rewrite history, and refunds post negative entries. Payroll runs through `payroll_periods` with multi-step approval and a hard lock (`locked_by_id`) before export; `employee_cost_components` (salary, allowances, GOSI) complete the true-cost picture per employee. _Targets: ~75% fewer scheduling conflicts; ~80% lighter HR admin burden._

## 5.3 CRM & Customer Intelligence
**Backing entities:** `customers`, `customer_preferences`, `customer_documents`, `clinical_notes`, `customer_segments`, `customer_segment_memberships`, `surveys`, `survey_responses`, `consent_records`.

360° customer profiles — identity, acquisition `source`, and lifecycle aggregates (`total_spent`, `visit_count`, `last_visit_at`, `loyalty_points`) maintained exclusively by background tasks; visit history, notes, secure documents, and communication log resolve through the relationship graph (appointments, sales, dispatches, conversations all FK to the customer). AI-computed LTV, churn probability, and next-visit prediction materialize as `AI`-type segments; `customer_segments.segment_type` distinguishes `MANUAL`, `DYNAMIC` (criteria JSON, refreshed with `last_refreshed_at` surfaced to marketers), `AI`, and `SYSTEM` lifecycle stages, with memberships diffed for journey triggers. NPS and post-visit surveys (`surveys.send_delay_hours`) capture `score`, `comment`, and AI-classified Arabic/English `sentiment`. PDPL-compliant consent is a dedicated ledger — `consent_records` per customer **per channel per purpose** with `granted_at`/`revoked_at`/`source`/`ip_address` provenance. _Targets: ~40% better personalization; ~25% churn reduction._

## 5.4 Booking, Waitlist & Queue Engine
**Backing entities:** `appointments`, `appointment_reminders`, `bookings`, `booking_attendees`, `booking_deposits`, `recurrence_rules`, `resources`, `resource_schedules`, `slot_holds`, `waitlist_entries`, `queue_tickets`, `cancellation_policies`.

24/7 self-service online booking with live availability across the staff + room + equipment triad (`employee_shifts` × `resource_schedules`) and **database-level double-booking prevention** — PostgreSQL exclusion constraints over `(employee_id, time-range)` and `(resource_id, time-range)` make conflicts physically impossible, not application-checked. Two aggregates share one calendar: `appointments` (1 customer × 1 employee × 1 service) and `bookings` (events/classes with `booking_attendees` and `recurrence_rules`), both carrying a `version` column for optimistic locking on drag-and-drop edits. Checkout-style booking races are absorbed by Redis-TTL holds mirrored to `slot_holds`. Smart waitlists (`waitlist_entries` with VIP priority and `booked_appointment_id` conversion tracking); walk-in virtual queues via QR/kiosk (`queue_tickets`: WAITING → CALLED → SERVING → SERVED) with live wait estimates; multi-touch reminders (`appointment_reminders` ladder per `organization_settings.reminder_hours`) over SMS/WhatsApp/email/push with two-way confirmation; deposits (`booking_deposits` via `payment_intents`) and `cancellation_policies` enforcement with service ▸ branch ▸ org precedence. _Targets: ~35% more bookings; ~50% fewer no-shows; ~20% better slot utilization._

## 5.5 Events & Ticketing
**Backing entities:** `events`, `ticket_types`, `tickets`, `ticket_verifications`, `bookings`.

Classes, workshops, and event series with capacity control; tiered ticket types (standard/VIP/early-bird) with atomic inventory (`quantity_sold` guarded against `quantity_available` at decrement — no oversell under concurrency) and dynamic pricing via `pricing_rules`; QR-secured digital tickets (signed-token payloads verifiable offline) with mobile scan verification, multi-entry passes (`valid_duration_minutes`), and a full check-in audit trail — every scan attempt, accepted or rejected, appends a `ticket_verifications` row with `verified_by_id`. _Targets: new revenue stream; ~70% faster entry; ~90% less ticket fraud._

## 5.6 Catalog, Packages & Dynamic Pricing
**Backing entities:** `service_categories`, `services`, `products`, `packages`, `package_items`, `customer_packages`, `package_redemptions`, `pricing_rules`.

Service and retail product catalogs with cost tracking and SKU management; bundles, memberships, and prepaid packages (`packages.package_type`) with validity (`validity_days` → `customer_packages.starts_at/expires_at`) and usage controls (`package_redemptions` decrementing `package_items.quantity`, each redemption linked to its appointment for utilization reporting). The dynamic pricing engine is a single deterministic rules table — `pricing_rules` scoped by any combination of branch/service/product/segment, conditioned on `days_of_week`, time windows, validity ranges, and **live utilization bands** (`min/max_utilization_percent` fed by daily branch metrics), resolved by `priority` with an explainable price trace stored on each sale line. _Targets: ~45% higher average transaction value; ~15% revenue lift from pricing optimization._

## 5.7 POS, Payments & Stored Value
**Backing entities:** `sales`, `sale_items`, `gift_cards`, `gift_card_transactions`, `store_credit_accounts`, `store_credit_transactions`, `payment_intents`, `payments`, `refunds`, `payment_webhook_events`, `settlements`, `settlement_lines`, `ledger_accounts`, `ledger_entries`, `document_sequences`.

Unified cart (services + products + packages + gift cards) in one transaction; split and partial payments, tips, deposits (refundable/non-refundable), full/partial refunds with an approval gate (`refunds.approver_id` must differ from requester above org thresholds). Moyasar gateway integration (mada, Visa/Mastercard, Apple Pay) follows a two-object model — `payment_intents` (the attempt) and `payments` (the fact) — with real-time webhooks deduplicated by `payment_webhook_events.gateway_event_id` and amounts verified against our records, never trusted from payloads. Daily settlement ingestion (`settlements` + `settlement_lines` matched to payments) reconciles gateway fees and computes the platform's payments margin. All stored value — digital and physical gift cards (`gift_card_transactions`) and store credit (`store_credit_transactions`) — runs as **append-only ledgers with cached balances**, and every financial event posts a balanced group to the immutable double-entry ledger (`ledger_accounts` / `ledger_entries`, Σdebit = Σcredit enforced) for audit-grade financial integrity. Gapless document numbering comes from row-locked `document_sequences`. _Targets: ~25% faster checkout; ~80% less billing admin._

## 5.8 ZATCA E-Invoicing (Phase 2)
**Backing entities:** `zatca_devices`, `zatca_counters`, `e_invoices`, `e_invoice_submissions`, `invoices`, `credit_notes`, `debit_notes`.

Per-device CSID onboarding (`zatca_devices`: PENDING_CSR → COMPLIANCE_CHECK → PRODUCTION_READY → ACTIVE, with `compliance_csid`/`production_csid` and envelope-encrypted private keys decrypted only inside the signing task); UBL 2.1 XML generation from the organization's native VAT/CR/national-address fields; cryptographic stamping, PIH chaining (`e_invoices.previous_invoice_hash`), and ICV sequencing serialized by a per-device row lock on `zatca_counters`; B2B clearance and B2C reporting flows; credit/debit notes with `reason_code` participating in the same hash chain; QR TLV on every invoice (`qr_code_tlv`); asynchronous submission with retry and full attempt history (`e_invoice_submissions.retry_count`, `api_response`) — invisible to the cashier, bulletproof for the auditor. A nightly chain-verification task walks every device chain and alerts on any ICV/PIH discontinuity. The entire subsystem sits behind an internal API so ZATCA spec changes never ripple into domain code (§14 mitigation, by construction).

## 5.9 Inventory & Procurement
**Backing entities:** `stock_movements`, `stock_transfers`, `suppliers`, `purchase_orders`, `purchase_order_lines`, `reorder_rules`.

Multi-location stock with an append-only movement ledger — **stock level is never a stored number**; on-hand per branch×product is the sum of `stock_movements` (typed: purchase receipt, sale deduction, internal use, transfer in/out, adjustment, waste, return), each movement linked to its originating document via `reference_type`/`reference_id`. Automatic sale deduction inside the sale transaction; approval-gated transfers (`stock_transfers`: REQUESTED → APPROVED → IN_TRANSIT → RECEIVED, with in-transit stock correctly "neither here nor there"); adjustments and waste logging with mandatory reasons; FIFO/LIFO valuation computed over receipt cost layers; reorder alerts (`reorder_rules` with `reorder_point`/`reorder_quantity`/`preferred_supplier_id` — nightly evaluation drafts POs for human approval, never auto-submits); supplier database and purchase orders with partial receiving (`quantity_received` guarded per line). _Targets: ~40% fewer stockouts; ~30% less excess inventory._

## 5.10 Marketing, Loyalty & Referrals
**Backing entities:** `campaigns`, `campaign_recipients`, `promotions`, `loyalty_programs`, `loyalty_transactions`, `referral_programs`, `referrals`, `journeys`, `journey_steps`.

Segment-targeted multi-channel campaigns (SMS, WhatsApp, email, push) with the recipient list snapshotted at send time into `campaign_recipients` (auditable "who got this and why"), A/B testing, open/click tracking, and ROI from attributed recipient revenue minus metered message costs. Discount codes (`promotions`) with usage and threshold rules (`max_uses` enforced atomically). Tiered points-based loyalty as an append-only ledger (`loyalty_transactions`: EARN/REDEEM/EXPIRE/ADJUST with `customers.loyalty_points` as cached balance). Dual-sided referral programs (`referrals`: PENDING → SIGNED_UP → QUALIFIED → REWARDED) with fraud validation before qualification — self-referral detection, per-customer caps (`max_referrals_per_customer`), minimum referee spend validated against **paid sales**, and refund clawback. Automated lifecycle journeys (`journeys` triggered by segment entry or events; `journey_steps` with ordered delays) with exit rules so conversion, consent revocation, or segment exit cancels remaining steps. _Targets: ~3x campaign ROI; ~25% retention lift; ~20% of new customers via referral._

## 5.11 Unified Communication Hub
**Backing entities:** `message_templates`, `message_dispatches`, `email_events`, `notifications`, `notification_templates`, `conversations`, `conversation_messages`, `consent_records`.

One dispatch pipeline for every outbound message — reminders, receipts, surveys, campaigns, journeys all flow through the same consent-and-quiet-hours gate before a `message_dispatches` row is queued (QUEUED → SENT → DELIVERED → READ, with per-message `cost` metered for re-billing). WhatsApp templates carry Meta's approval lifecycle natively (`message_templates.approval_status` + `template_id_external` via Unifonic); SES email events ingest idempotently (`email_events.sns_message_id` unique) with hard bounces auto-revoking email consent. One inbox: `conversations` (OPEN → PENDING_CUSTOMER → RESOLVED) routed to branch staff via `assigned_to_id`, with `conversation_messages` linking outbound entries to their dispatch for true delivery/read state, and structured replies ("1" = confirm) short-circuiting to domain actions. Multi-language template library with variable substitution; in-app `notifications` with read tracking. _Targets: ~95% reach rate; ~40% faster response times._

## 5.12 Analytics, BI & Goals
**Backing entities:** `analytics_events`, `reports`, `daily_metrics`, `daily_branch_metrics`, `daily_employee_metrics`, `goals`, `goal_milestones`.

Real-time role-specific dashboards reading from pre-aggregated rollups — `daily_metrics` (org×day), `daily_branch_metrics` (branch×day incl. no-shows and `avg_wait_time_minutes`), `daily_employee_metrics` (employee×day incl. revenue, commission, `utilization_percent`) — never from raw transactional tables at request time. Append-only, time-partitioned `analytics_events` with per-row `retention_months`. Operational, financial, customer, and marketing report suites generated asynchronously (`reports.parameters` → bilingual PDF/XLSX at `file_url`). Branch benchmarking; anomaly detection comparing daily metrics against Ramadan-aware seasonal baselines; multi-level goal setting (`goals` at org/branch/individual on any rollup metric: ACTIVE → ACHIEVED/MISSED) with `goal_milestones` at threshold percentages driving rewards and leaderboards.

## 5.13 AI Suite
**Backing entities:** `ai_conversations`, `ai_messages`, `ai_recommendations` (+ the entire tenant schema as the training surface).

Demand and revenue forecasting (Hijri/Ramadan-aware seasonality); churn and LTV models scoring into AI segments; smart staff allocation combining demand forecasts with qualifications and true employee costs; Arabic/English marketing copy and service-description generation (drafts only — human review before any send); a conversational AI assistant (`ai_conversations`/`ai_messages` with per-message `tokens_used` metering) answering natural-language business questions strictly on the tenant's own data through guarded, tenant-scoped, RBAC-enforced query tools — never raw SQL; AI report summaries. All model outputs land as `ai_recommendations` (NEW → VIEWED → ACTED/DISMISSED, each carrying its evidence payload in `data`) — **recommendations, never silent automatic actions**; acted/dismissed feedback becomes training signal. _Targets: ~50% less analysis time; ~25% better resource planning._

## 5.14 Forms, Documents & Clinical Records
**Backing entities:** `clinical_notes`, `customer_documents`, `consent_records`, `access_logs`.

Drag-and-drop form builder (intake, consent, medical history, feedback) with conditional logic and legally-compliant e-signatures; encrypted document vault (`customer_documents.file_url_encrypted`, presigned short-TTL access) with expiry alerts, versioning, and permission-scoped access. Clinical notes are a segregated, field-encrypted domain — `clinical_notes.content_encrypted` under per-tenant envelope keys, plaintext never touching logs or indexes — with **mandatory access logging**: every read writes an `access_logs` row, enforced at the model-manager level so no query path can bypass it, and RBAC restricting contents to clinical roles only.

## 5.15 Localization
**Backing entities:** `translations`, `countries`, `currencies`, plus branch-level Gulf fields.

Native Arabic RTL and English LTR with additional languages (French, Urdu); per-organization language configuration; content translation for services, products, and templates via the polymorphic per-tenant `translations` table (`entity_type`/`entity_id`/`locale`/`field`) resolved requested-locale → org-default → base column and bulk-prefetched per page; regional date/time formats and Hijri display (`branches.hijri_display_preference`) — the database stores Gregorian UTC exclusively; Hijri and Arabic numerals are presentation-layer.

## 5.16 Integrations & Open Platform
**Backing entities:** `api_keys`, `webhook_endpoints`, `webhook_deliveries`, `outbound_events`, `integration_connections`, `devices`, `sync_operations`.

Two-way Google/Outlook/Apple calendar sync, QuickBooks and Xero accounting sync (daily journal summaries from the ledger — never line-level customer PII), Mailchimp (consent-respecting segment sync only) and social booking (Instagram/Facebook) — all through `integration_connections` with envelope-encrypted credentials and circuit breakers so a dead integration never degrades core operations. Organization-defined webhooks (`webhook_endpoints` with HMAC signing secrets, subscribed event lists) delivered from the transactional outbox (`outbound_events`) with per-delivery retry/backoff audit (`webhook_deliveries`) and auto-disable on sustained failure. Full REST API with OAuth 2.0 and API keys (`key_prefix` + `key_hash`, scoped, rotatable without downtime, rate-limited by tenant tier). The offline device layer (`devices` + `sync_operations`) gives branch POS resilience: offline devices **queue, never finalize** financial operations — cash sales replay through the same domain services with conflict status/resolution recorded per operation, sale and invoice numbers always minted server-side.

## 5.17 Security & Trust
**Backing entities:** `users`, `user_roles`, `user_sessions`, `two_factor_devices`, `audit_logs`, `access_logs`, `idempotency_records`, `retention_policies`.

Encryption at rest and in transit; strict multi-tenant isolation — `organization_id` on every tenant row with PostgreSQL row-level security on the shared tier, dedicated isolated databases for Enterprise; tenant scope resolved by middleware from the authenticated principal, never accepted from request bodies. 2FA (`two_factor_devices`); session and device management (`user_sessions` with per-session refresh-token JTI, device labels, and revocation); branch- and function-scoped RBAC (`user_roles`). Append-only `audit_logs` (old/new values, IP, user agent) on every state transition and `access_logs` on every sensitive read, both time-partitioned; configurable retention (`retention_policies` per entity type driving anonymize/delete sweeps — financial records anonymized, never deleted, preserving ZATCA obligations); PDPL data-subject export and deletion; idempotency on every mutating endpoint (`idempotency_records` replaying stored responses verbatim); automated backups with point-in-time recovery; in-Kingdom hosting options.

---

# 6. Platform Architecture & Tech Stack
| Layer | Technology | Why |
| ----- | ----- | ----- |
| Web frontend | **SvelteKit 2.x (SSR) + Svelte 5 Runes + Tailwind CSS v4** | Fastest-loading premium UI in class; SEO-ready booking pages per tenant; pure JavaScript |
| Mobile | **PWA with offline queueing** | Installable, branch-resilient; offline devices queue (never finalize) financial operations — `devices` + `sync_operations`  |
| API & business logic | **Django + Django REST Framework (Python)** | Mature, secure, rapid multi-tenant development; strict typing |
| Real-time | **Django Channels / SSE** | Live calendars, queue displays, POS payment confirmations |
| Database | **PostgreSQL** | <p>**123-entity relational model across 13 domains**</p><p>; row-level security; exclusion constraints that make double-booking physically impossible; time-partitioned event/audit tables</p> |
| Cache, holds & broker | **Redis** | Session state, slot-hold TTLs (`slot_holds` mirror), message brokering |
| Async processing | **Celery workers + beat** | ZATCA submissions, campaign sends, report generation, webhooks (outbox pattern via `outbound_events`) |
| Storage | **S3-compatible, per-tenant prefixes** | Documents, media, invoice XML archive (`e_invoices.ubl_xml_url`) |
| Payments | <p>**Moyasar**</p><p> (mada, Visa/MC, Apple Pay)</p> | Idempotent webhook processing (`payment_webhook_events`); settlement reconciliation (`settlements`) |
| Messaging | <p>**Unifonic**</p><p> (SMS + WhatsApp Business)</p> | Template lifecycle management (`message_templates.approval_status`); delivery callbacks; metered cost re-billing (`message_dispatches.cost`) |
| Email | **Amazon SES** | Transactional + campaign delivery at scale; SNS event ingestion (`email_events`) |
| Hosting | AWS (Riyadh region available) / GCC cloud options | Data residency for regulated and Enterprise customers |
## 6.1 Domain Map (the 13 model domains → Django apps)
```
namaa/
├── core/            countries, currencies, translations, audit_logs,
│                    access_logs, idempotency_records
├── accounts/        users, user_roles, user_sessions, two_factor_devices
├── organizations/   organizations, organization_settings, branches,
│                    branch_hours, retention_policies
├── customers/       customers, customer_preferences, clinical_notes,
│                    customer_documents, customer_segments,
│                    customer_segment_memberships, surveys, survey_responses
├── commerce/        service_categories, services, products, sales, sale_items,
│                    gift_cards, gift_card_transactions, store_credit_accounts,
│                    store_credit_transactions, packages, package_items,
│                    customer_packages, package_redemptions, pricing_rules
├── scheduling/      appointments, appointment_reminders, bookings,
│                    booking_attendees, booking_deposits, events,
│                    recurrence_rules, ticket_types, tickets,
│                    ticket_verifications, resources, resource_schedules,
│                    slot_holds, cancellation_policies, queue_tickets,
│                    waitlist_entries
├── workforce/       employees, employee_schedules, employee_services,
│                    employee_shifts, payroll_periods, commission_entries,
│                    commission_rules, employee_cost_components
├── finance/         document_sequences, invoices, credit_notes, debit_notes,
│                    payment_intents, payments, refunds, payment_webhook_events,
│                    settlements, settlement_lines, ledger_accounts, ledger_entries
├── zatca/           zatca_devices, zatca_counters, e_invoices,
│                    e_invoice_submissions        ← isolated behind internal API
├── billing/         plans, plan_entitlements, subscriptions,
│                    subscription_invoices, usage_records, dunning_attempts
├── inventory/       stock_movements, stock_transfers, suppliers,
│                    purchase_orders, purchase_order_lines, reorder_rules
├── messaging/       message_templates, message_dispatches, email_events,
│                    consent_records, notifications, notification_templates,
│                    conversations, conversation_messages
├── marketing/       campaigns, campaign_recipients, promotions,
│                    loyalty_programs, loyalty_transactions, referral_programs,
│                    referrals, journeys, journey_steps
├── analytics/       analytics_events, reports, daily_metrics,
│                    daily_branch_metrics, daily_employee_metrics,
│                    goals, goal_milestones
├── ai/              ai_conversations, ai_messages, ai_recommendations
└── integrations/    api_keys, webhook_endpoints, devices, sync_operations,
                     outbound_events, webhook_deliveries, integration_connections
```
Dependency direction enforced by import-linter: `core` ← `accounts` ← `organizations` ← everything else; domain apps cross the money boundary only through service functions, never raw cross-app joins in business logic.

## 6.2 The Signature Decision Flow — "One Transaction, Five Engines"
A cashier completes a checkout; the system fans out across every engine:

```
POS Checkout (SvelteKit, < 1s perceived)
        │
        ▼  POST /api/v1/sales   (Idempotency-Key header — mandatory)
┌──────────────────────────────────────────────────────────────┐
│ SYNCHRONOUS — single DB transaction (SELECT ... FOR UPDATE)   │
│  1. Validate cart: services / products / packages / gift cards│
│  2. Apply pricing_rules by priority → explainable price trace │
│  3. sales + sale_items  (status = COMPLETED)                  │
│  4. stock_movements deduction (append-only)                   │
│  5. invoices numbered from locked document_sequences (gapless)│
│  6. ledger_entries posted (double-entry, must balance)        │
│  7. outbound_events row written (transactional outbox)        │
│  COMMIT                                                       │
└──────────────────────────────────────────────────────────────┘
        │   transaction.on_commit →
        ▼
┌──────────────────────────────────────────────────────────────┐
│ ASYNCHRONOUS — Celery, retried with exponential backoff       │
│  A. ZATCA: lock zatca_counters → ICV/PIH → sign → e_invoices  │
│     → clearance (B2B) / reporting (B2C) → e_invoice_submissions│
│  B. Moyasar capture (if card) → payments → settlements later  │
│  C. Commission: resolve commission_rules → commission_entries │
│  D. Receipt: consent gate → message_dispatches → Unifonic/SES │
│  E. analytics_events ingestion → nightly rollups              │
│  F. Loyalty earn, journey evaluation, milestone checks        │
│  G. Webhook fan-out → webhook_deliveries                      │
└──────────────────────────────────────────────────────────────┘
```
**The rule this flow encodes:** the cashier waits only for the database. Every third party (ZATCA, Moyasar, Unifonic, SES) is downstream of the commit, retried independently, and its failure can never roll back a sale.

## 6.3 Architecture Principles (model-enforced)
- **API-first.** REST under `/api/v1/` ; OAuth 2.0 + scoped API keys for the open platform; cursor pagination; bilingual RFC-7807 errors.
- `**tenant_id**`  **on every row with RLS enforcement** — `organization_id`  is middleware-resolved from the authenticated principal, never accepted from request bodies.
- **Explicit state machines (never boolean flags)** for bookings, appointments, payments, invoices, e-invoices, subscriptions, transfers, referrals, and every other lifecycle — each `status`  column is a Django `TextChoices`  enum with a declared transition graph; transitions run through a single service that validates the edge, bumps `version`  where present, writes `audit_logs` , and emits `outbound_events` .
- **Immutable ledgers for money and stock** — `ledger_entries` , `stock_movements` , `gift_card_transactions` , `store_credit_transactions` , `loyalty_transactions`  are append-only; corrections are reversing entries, never updates; cached balances are nightly-reconciled conveniences, the ledger is truth.
- **Idempotency keys on every mutating endpoint** — `idempotency_records`  replays stored responses verbatim on duplicate keys; the same mechanism makes offline sync replay and gateway webhook redelivery safe.
- **Concurrency doctrine:** exclusion constraints for double-booking; row-locked sequences and counters (`document_sequences` , `zatca_counters` ) with canonical lock ordering (sequence → sale → stock → ledger) and deadlock retry; optimistic `version`  columns on calendars; Redis slot-holds with `slot_holds`  as truth; atomic guarded decrements for ticket inventory and promotion usage.
- **Query doctrine:** every list endpoint declares its `select_related` /`prefetch_related`  set with CI-asserted query budgets on hot paths (calendar day view, POS catalog, invoice list); dashboards read `daily_*`  rollups, never raw transactional tables at request time; `analytics_events` , `audit_logs` , `access_logs` , webhook/dispatch tables are time-partitioned monthly.
- **Horizontal, stateless scaling** — workers claim outbox/dispatch work with `SKIP LOCKED` ; scale by adding workers.
---

# 7. Regulatory & Legal Position (KSA)
Namaa is engineered around — and differentiated by — the Saudi regulatory stack:

- **ZATCA (Fatoora):** Full Phase-2 integration capability (§5.8), modeled as a dedicated, internally-isolated subsystem (`zatca_devices` , `zatca_counters` , `e_invoices` , `e_invoice_submissions` ). We pursue certified-solution-provider status as a marketing asset, not just a feature.
- **PDPL (Personal Data Protection Law):** Consent records per customer per channel per purpose (`consent_records`  with grant/revoke provenance — every marketing send stores the consent row it relied on); data-subject export/deletion; processing registers; in-Kingdom residency options. Health-related notes are sensitive data with field-level encryption (`clinical_notes.content_encrypted` ) and mandatory access logging (`access_logs` ). Retention is policy-driven per entity type (`retention_policies` ); financial records are anonymized rather than deleted where ZATCA retention obligations override erasure.
- **E-signature validity:** Digital intake/consent signatures aligned with the Saudi Electronic Transactions Law.
- **Payments perimeter:** Namaa does not hold client funds — settlement flows through licensed gateways (Moyasar; reconciled in `settlements` ), keeping us outside SAMA licensing requirements at launch while we evaluate SoftPOS/aggregation authorization as a later strategic step.
- **Commercial posture:** Saudi LLC, MISA/CR registration, VAT registration, customer contracts with Saudi governing law, and clear SaaS terms (uptime SLA tiers, data ownership remains with the customer).
---

# 8. Business Model & Pricing (SAR, VAT-exclusive)
A four-tier value ladder plus usage-based layers, implemented end-to-end in the model's billing domain (`plans`, `plan_entitlements`, `subscriptions`, `subscription_invoices`, `usage_records`, `dunning_attempts`). ZATCA Phase-2 integration is **included from Growth tier upward** — compliance is our wedge, never a penalty fee.

|  | **انطلاقة Launch** | **نمو Growth** | **توسع Expansion** | **مؤسسات Enterprise** |
| ----- | ----- | ----- | ----- | ----- |
| Monthly (billed annually) | **449** | **1,200** | **3,500** | <p>Custom, from </p><p>**95,000/yr**</p> |
| Month-to-month | 549 | 1,450 | 4,200 | Multi-year contracts |
| Branches / Staff | 1 / 5 | 1 / 15 | up to 5 (+600/mo extra) / unlimited | Unlimited / unlimited |
| Core suite (booking, POS, CRM, invoicing) | ✔ | ✔ | ✔ | ✔ |
| ZATCA Phase 2 live | +150/mo | Included | Included | Included |
| Loyalty / Ticketing / Advanced BI | — | Loyalty | All | All |
| AI Suite | — | +500/mo | +500/mo | Included |
| Official WhatsApp channel | — | +300/mo + usage | +300/mo + usage | Included + usage |
| Support & infrastructure | Self-serve | Priority | Dedicated CSM | Account manager, SLA, isolated DB |
**How the model enforces the ladder:** tiers are `plans`; every gate in the table is a `plan_entitlements` row (`feature_key`, `limit_value`, `is_enabled`) checked by a single Redis-cached entitlement service. Limits behave commercially, not destructively — exceeding the branch count blocks creating the _next_ branch and surfaces the upgrade path; it never disables existing data. Subscription lifecycle: `TRIALING → ACTIVE → PAST_DUE → SUSPENDED → CANCELLED` with `PAUSED` support; failed charges run a `dunning_attempts` ladder (retry → notices → grace period → soft suspension: read-only access, never data deletion).

**Usage-based revenue layers (the ARPU engine):**

1. **Payments margin:** 0.4–0.8% platform spread on card volume processed through embedded Moyasar acceptance — computed at settlement reconciliation (`settlements.gateway_fees`  vs. merchant-facing rate); revenue that grows automatically with each customer's success.
2. **Messaging margin:** ~20–25% markup on metered SMS/WhatsApp volume — per-message `cost`  captured on every `message_dispatches`  row, rolled into `usage_records` .
3. **Onboarding & migration:** 1,500 / 4,000 / 15,000+ SAR by tier — funds white-glove Arabic onboarding and filters for committed buyers.
4. **Add-on attach:** AI Suite (metered via `ai_messages.tokens_used`  → `usage_records` ) and WhatsApp channel target >35% attach on Growth+ by month 18.
**Unit-economics design targets:** logo churn <2%/month by month 12; NRR >110% (branch expansion + add-ons + payments); blended CAC payback <9 months; Launch tier acquired at near-zero CAC (self-serve).

---

# 9. Financial Plan & The Ask
**Illustrative trajectory (base case, subscription + ~30% usage layers):**

| Milestone | Customers (L/G/E/Ent) | ARR run rate |
| ----- | ----- | ----- |
| Month 12 | 120 / 90 / 12 / 1 | **~3.4M SAR (~USD 0.9M)** |
| Month 24 | 350 / 280 / 45 / 5 | **~11.3M SAR (~USD 3.0M)** |
Requires ~20–25 net-new paying customers/month from month 4 — fully costed in the GTM plan (§10).

**Use of seed funds (indicative allocation over 18 months):**

- 45% — Engineering & product (core team of 6–8, ZATCA certification, AI suite v1)
- 30% — Go-to-market (2 AEs, field sales, paid acquisition, LEAP/Biban/Seamless presence)
- 15% — Customer success & onboarding (the churn-killer investment)
- 10% — Legal, compliance, infrastructure, working capital
**Why investors win here:** a regulatory tailwind that compels adoption; a payments layer that converts SaaS into fintech-grade economics; Arabic-first defensibility against global entrants; a land-and-expand model (branch growth is built into the customer's own ambition — and into the schema, where adding a branch is a row, not a migration); and a clear GCC expansion path where the hardest asset — the compliance engine — transfers market to market.

---

# 10. Go-To-Market Summary (Full plan maintained separately)
- **Phase 0 (Mo 0–3):** 12–15 Riyadh/Jeddah design partners in two beachhead verticals (salons + clinics); ZATCA certification; filmed Arabic case studies with real numbers; Monsha'at ecosystem registration.
- **Phase 1 (Mo 4–9):** Public launch timed to LEAP/Biban; Arabic-first paid acquisition (Google intent keywords, Snapchat/TikTok/Meta owner-targeting); 2-person field-sales motion where the live 20-minute demo is the close; channel partners (Moyasar co-marketing, POS resellers, accountants as ZATCA referrers); dual-sided referral program.
- **Phase 2 (Mo 10–18):** Entertainment/ticketing vertical launch; ABM outbound to every 3–15-branch chain in KSA; Arabic SEO content moat; monthly webinars; "Namaa Majlis" customer community dinners; Dammam/Khobar coverage.
- **Phase 3 (Mo 19–24):** UAE entry via implementation partners (e-invoicing muscle transfers); Qatar/Kuwait partner-led; enterprise AE hire targeting hospitality, franchise, and healthcare groups; brand campaign built on 20+ filmed success stories; strategic distribution talks (telco SME bundles).
**Weekly scoreboard:** new paying customers; demo→paid ≥30%; logo churn <2%/mo; NRR >110%; CAC payback <9 months.

---

# 11. Team & Organization Plan
| Phase | Core roles |
| ----- | ----- |
| Build (Mo 0–6) | Founder/CEO (product + sales); CTO/lead engineer; 2 full-stack engineers (Django/SvelteKit); 1 product designer (Arabic-first); part-time compliance/finance advisor |
| Launch (Mo 4–12) | +2 Arabic-speaking AE/SDRs; +1 customer success/onboarding lead; +1 content marketer (Arabic) |
| Scale (Mo 12–24) | +2 engineers (AI/data + payments); +2 CS; +1 growth marketer; +1 enterprise AE; +1 partner manager (GCC) |
Culture commitments: bilingual by default; customer-onsite Fridays for engineers; commission transparency internally (we sell it, we live it); Saudization-aligned hiring plan as we scale.

---

# 12. Operations Playbook (Run-the-Business Standard)
- **Onboarding:** white-glove for Growth+ — data migration from spreadsheets/legacy tools, service catalog setup, staff training in Arabic, ZATCA device onboarding (`zatca_devices`  CSID flow) — completed inside 10 business days, owned by CS with a go-live checklist.
- **Support tiers:** self-serve knowledge base + chat (Launch); priority chat <2h business-hours response (Growth); dedicated CSM with quarterly business reviews showing the customer their own ROI numbers from their own rollup metrics (Expansion); named account manager with contractual SLA (Enterprise).
- **Reliability:** 99.9% target uptime; status page; point-in-time recovery; incident communication templates in Arabic and English.
- **Billing operations:** annual-first invoicing; dunning with grace periods (`dunning_attempts`  ladder — suspension is read-only access, never data deletion); pause capability (`subscriptions`  PAUSED state); proration on plan changes.
- **Voice of customer:** NPS quarterly (through the same `surveys`  engine we sell); churn interviews mandatory within 7 days of any cancellation (triggered by `subscriptions.cancelled_at` ); product council drawn from top 15 customers.
---

# 13. UI / UX Design Language — "Namaa Premium Arabic-First"
The interface is a sales asset. Design system principles:

- **Identity:** the Namaa mark evokes growth (نماء) — an upward organic curve. Palette: deep green (trust, growth, Saudi identity) anchored by warm sand neutrals, with a gold accent reserved exclusively for revenue moments (payment success, goal achieved). Dark mode as a first-class theme for reception desks operating at night.
- **Typography:** a premium Arabic-Latin pairing (e.g., IBM Plex Sans Arabic class) with true RTL mirroring of every layout, icon direction, and chart axis — not flipped-CSS approximations.
- **Layout system:** role-based home screens — the owner lands on a live revenue pulse (fed by `daily_metrics` ); the receptionist lands on today's calendar and queue; the cashier lands on POS. Three-click rule: any daily action (book, sell, check-in) reachable in ≤3 interactions.
- **POS screen:** touch-first, glove-friendly targets, keyboard-free checkout, sub-second product search, offline state always visible (amber banner, queued-operations counter reading directly from the `sync_operations`  queue).
- **Calendar:** drag-and-drop with live conflict shading across staff/room/equipment (optimistic `version`  locking — stale edits get a polite refresh, never silent overwrites); prayer-time and Ramadan-hours bands rendered natively on the timeline from branch-level schema fields.
- **Data visualization:** numbers before charts — every dashboard tile leads with the figure and trend arrow; charts use the same green/sand language; Arabic numerals per organization preference.
- **Micro-interactions:** purposeful, fast (under 200ms), never decorative on operational screens; celebratory moments (goal hit, milestone reached — `goal_milestones.reached_at` ) get one tasteful animation.
- **Accessibility & trust:** WCAG-AA contrast, full bilingual parity (no English-only corners), ZATCA QR (`e_invoices.qr_code_tlv` ) rendered beautifully on invoices, and consent prompts written in plain Arabic.
---

# 14. Risks & Mitigations
| Risk | Mitigation |
| ----- | ----- |
| Global competitor localizes (Fresha/Zenoti) | Compliance depth + payments embed + Arabic CS create switching costs they won't replicate quickly; speed to 500 logos |
| ZATCA spec changes | Compliance module isolated behind an internal API — the four ZATCA entities live in their own app; domain code only enqueues and reads status; dedicated regulatory watch; certified-provider relationship with ZATCA |
| SMB churn culture | Onboarding investment, annual billing, stored-value lock-in (gift cards/packages — modeled as liability ledgers customers won't abandon), QBRs showing ROI |
| Payments margin compression | Multi-gateway abstraction (`payments.gateway` is a field, not an assumption); volume-tiered Moyasar terms; SoftPOS path |
| Key-person dependency | Documentation-first engineering (this document + the model are the single source of truth); playbooks for sales/CS from day one |
| Funding-market timing | Lean base case reaches default-alive on Expansion-tier revenue + onboarding fees |
---

# 15. Roadmap Milestones
- **M3:** Platform beta live with 12+ design partners; ZATCA sandbox certified.
- **M6:** Public launch; payments margin live; 40+ paying customers.
- **M9:** 100 customers; AI Suite v1 (churn + demand forecast); WhatsApp official channel GA.
- **M12:** ~3.4M SAR ARR run rate; ticketing vertical GA; Series-A-ready metrics pack.
- **M18:** 400+ customers; enterprise tier live with isolated infrastructure; Dammam coverage.
- **M24:** UAE live via partners; ~11M SAR ARR run rate; GCC partner network in 3 markets.
---

# Appendix A — Canonical Data Model Index (123 Entities, 13 Domains)
| Domain | Entities | Feature §§ |
| ----- | ----- | ----- |
| <p>**Core / Platform**</p><p> (6)</p> | countries, currencies, translations, audit_logs, access_logs, idempotency_records | 5.15, 5.17, 6.3 |
| <p>**Accounts**</p><p> (4)</p> | users, user_roles, user_sessions, two_factor_devices | 5.2, 5.17 |
| <p>**Organizations**</p><p> (5)</p> | organizations, organization_settings, retention_policies, branches, branch_hours | 5.1, 5.15 |
| <p>**Customers**</p><p> (8)</p> | customers, customer_preferences, clinical_notes, customer_documents, customer_segments, customer_segment_memberships, surveys, survey_responses | 5.3, 5.14 |
| <p>**Commerce / Catalog**</p><p> (14)</p> | service_categories, services, products, sales, sale_items, gift_cards, gift_card_transactions, store_credit_accounts, store_credit_transactions, packages, package_items, customer_packages, package_redemptions, pricing_rules | 5.6, 5.7 |
| <p>**Operations**</p><p> (25)</p> | employees, employee_schedules, employee_services, employee_shifts, recurrence_rules, events, appointments, appointment_reminders, bookings, booking_attendees, booking_deposits, ticket_types, tickets, ticket_verifications, resources, resource_schedules, slot_holds, cancellation_policies, queue_tickets, payroll_periods, commission_entries, commission_rules, employee_cost_components, waitlist_entries, document_sequences* | 5.2, 5.4, 5.5 |
| <p>**Financials**</p><p> (22)</p> | document_sequences*, invoices, credit_notes, debit_notes, payment_intents, payments, refunds, payment_webhook_events, settlements, settlement_lines, ledger_accounts, ledger_entries, zatca_devices, zatca_counters, e_invoices, e_invoice_submissions, plans, plan_entitlements, subscriptions, subscription_invoices, usage_records, dunning_attempts | 5.7, 5.8, §8 |
| <p>**Inventory**</p><p> (6)</p> | stock_movements, stock_transfers, suppliers, purchase_orders, purchase_order_lines, reorder_rules | 5.9 |
| <p>**Communications**</p><p> (8)</p> | message_templates, message_dispatches, email_events, consent_records, notifications, notification_templates, conversations, conversation_messages | 5.11, 5.3 |
| <p>**Marketing**</p><p> (9)</p> | campaigns, campaign_recipients, promotions, loyalty_programs, loyalty_transactions, referral_programs, referrals, journeys, journey_steps | 5.10 |
| <p>**Analytics**</p><p> (7)</p> | analytics_events, reports, daily_metrics, daily_branch_metrics, daily_employee_metrics, goals, goal_milestones | 5.12 |
| <p>**AI Assistant**</p><p> (3)</p> | ai_conversations, ai_messages, ai_recommendations | 5.13 |
| <p>**Integrations**</p><p> (7)</p> | api_keys, webhook_endpoints, devices, sync_operations, outbound_events, webhook_deliveries, integration_connections | 5.16 |
_*_`_document_sequences_` _is declared in the Financials section of the diagram and serves both sale and invoice numbering._

# Appendix B — Canonical State Machines (status enums, never booleans)
| Entity | Lifecycle |
| ----- | ----- |
| appointments | PENDING → CONFIRMED → IN_PROGRESS → COMPLETED | NO_SHOW | CANCELLED |
| bookings | DRAFT → PENDING_PAYMENT → CONFIRMED → COMPLETED | CANCELLED | EXPIRED |
| tickets | ISSUED → ACTIVE → CHECKED_IN(×N) → USED | EXPIRED | CANCELLED | REVOKED |
| queue_tickets | WAITING → CALLED → SERVING → SERVED | NO_SHOW | LEFT |
| waitlist_entries | ACTIVE → OFFERED → BOOKED | DECLINED | EXPIRED | CANCELLED |
| sales | DRAFT → PENDING_PAYMENT → COMPLETED → PARTIALLY_REFUNDED → REFUNDED (VOIDED pre-payment only) |
| invoices | DRAFT → ISSUED → PARTIALLY_PAID | OVERDUE → PAID (immutable once issued; corrections via credit/debit notes) |
| payment_intents | CREATED → REQUIRES_ACTION → PROCESSING → SUCCEEDED | FAILED | EXPIRED | CANCELLED |
| payments | PENDING → SUCCEEDED → PARTIALLY_REFUNDED | REFUNDED (FAILED terminal) |
| refunds | PENDING → APPROVED → REFUNDED | FAILED (approver ≠ requester above threshold) |
| zatca_devices | PENDING_CSR → COMPLIANCE_CHECK → PRODUCTION_READY → ACTIVE → SUSPENDED | REVOKED |
| e_invoices | PENDING → SIGNED → SUBMITTED → CLEARED | REPORTED | WARNING | REJECTED |
| subscriptions | TRIALING → ACTIVE ⇄ PAUSED; ACTIVE → PAST_DUE → SUSPENDED → CANCELLED |
| stock_transfers | REQUESTED → APPROVED → IN_TRANSIT → RECEIVED | REJECTED | CANCELLED |
| purchase_orders | DRAFT → SUBMITTED → CONFIRMED → PARTIALLY_RECEIVED → RECEIVED → CLOSED | CANCELLED |
| message_dispatches | QUEUED → SENT → DELIVERED → READ | FAILED | DROPPED_NO_CONSENT |
| message_templates (WhatsApp) | DRAFT → SUBMITTED → APPROVED | REJECTED |
| conversations | OPEN → PENDING_CUSTOMER → RESOLVED (reopens on inbound) |
| campaigns | DRAFT → SCHEDULED → SENDING → SENT | CANCELLED |
| referrals | PENDING → SIGNED_UP → QUALIFIED → REWARDED | REJECTED |
| commission_entries | PENDING → APPROVED → PAID (DISPUTED → ADJUSTED side path) |
| payroll_periods | OPEN → CALCULATING → PENDING_APPROVAL → LOCKED → EXPORTED |
| goals | ACTIVE → ACHIEVED | MISSED | CANCELLED |
| ai_recommendations | NEW → VIEWED → ACTED | DISMISSED |
| customer_packages | ACTIVE → DEPLETED | EXPIRED | CANCELLED | FROZEN |
| gift_cards | ACTIVE → DEPLETED | EXPIRED | BLOCKED |
---

_Namaa — نماء. Where Gulf service businesses grow._ _Prepared June 2026 (v2.1, model-aligned). Figures marked as targets/estimates are internal projections for planning and discussion, to be validated in diligence._

