* # Namaa Founder Playbook — Practical Tips

  ## Law • Money • Operations • Team • Tech Stack • Marketing • Strategy • UI Design

  ### Companion file to the Master Documentation (June 2026)

  > Working guidance for the founder. Items marked ⚖️ require confirmation with a licensed Saudi lawyer or accountant — this document is operational guidance, not legal or financial advice.

  ------

  ## 1. Law & Compliance Tips (KSA)

  1. ⚖️ **Incorporate as a Saudi LLC early** with a clean cap table and founder vesting (4 years, 1-year cliff) documented from day one — investors will ask, and retrofitting vesting after co-founder friction is painful.
  2. ⚖️ **Register for VAT before invoicing customers**, and remember your *own* invoices to customers must be ZATCA-compliant — run Namaa on Namaa from the first sale. It's the best demo you'll ever have.
  3. **Pursue ZATCA certified-solution-provider listing** as soon as the e-invoicing module passes sandbox tests. The listing itself is a sales and trust asset, and accountants browse it when advising clients.
  4. ⚖️ **Treat PDPL as a product feature, not paperwork:** appoint a data-protection contact, maintain a record of processing activities, and make consent capture/withdrawal visible in the UI. Your clinic customers process health data — your DPA (data processing agreement) template must exist before the first clinic signs.
  5. **Never touch client funds.** Keep settlement flowing gateway→merchant directly. The moment money rests in your accounts, you enter SAMA licensing territory — defer that strategic decision until payments volume justifies counsel and capital. ⚖️
  6. **Contracts:** one master SaaS agreement (Arabic governing version, English courtesy translation), order forms per tier, an SLA schedule, and a DPA annex. Cap your liability at 12 months of fees; exclude indirect damages; keep customer data ownership explicitly with the customer.
  7. **Trademark «نماء / Namaa» in KSA (SAIP) immediately** in the software and business-services classes, and secure the .sa domain — name disputes after traction are expensive.
  8. **Employment:** use compliant Saudi labor contracts via Qiwa from the first hire; document IP-assignment clauses for every engineer and designer, including freelancers — investors diligence this hard.

  ## 2. Money Tips

  1. **Default-alive math first:** know the exact customer count at which Expansion-tier revenue + onboarding fees cover payroll. Make every spending decision against that number, not against the fundraise narrative.
  2. **Annual billing is your friend twice:** it funds CAC upfront and it suppresses churn. Quote annual by default; treat monthly as the premium-priced exception.
  3. **Separate the three money streams in your books from day one** — subscriptions, usage (messages/payments margin), services (onboarding) — investors price recurring revenue differently from services, and mixing them poisons your multiple.
  4. **Watch gross margin on messaging:** WhatsApp/SMS costs scale with customer success; re-bill with margin and meter it. An unmonitored notification feature can quietly destroy 10 points of gross margin.
  5. **Discount with commitment, never with desperation:** any discount >15% must buy something — a 2-year term, a filmed case study, a referenceable logo. Train sales that price integrity *is* the brand.
  6. **Collections discipline:** dunning automation, card-on-file mandatory for monthly plans, service pause (not data deletion) at +21 days overdue. Be generous in tone, rigid in process.
  7. **Raise when you have a repeatable motion, not a finished product:** the strongest seed story is 15 design partners, 3 filmed case studies, and a demo→paid conversion number — not 70 database tables.

  ## 3. Operations Tips

  1. **Onboarding is your churn weapon.** A customer who completes data migration + staff training + first ZATCA invoice within 10 days almost never churns. Track "time-to-first-live-invoice" as a company-level KPI.
  2. **Run churn autopsies religiously:** founder-led call within 7 days of every cancellation, written one-pager, monthly pattern review. In SMB SaaS, churn causes cluster fast — catch the cluster early.
  3. **Build the support knowledge base in Arabic first**, with 60-second screen-recording videos — your users are receptionists and cashiers, not IT staff.
  4. **QBRs that show the customer their own money:** revenue lift, no-shows prevented, hours saved — pulled live from their dashboard. This single ritual drives renewals, add-on attach, and referrals simultaneously.
  5. **Status page + incident honesty:** Gulf SMBs forgive downtime; they never forgive silence. Pre-write bilingual incident templates before you need them.
  6. **Document every internal process the third time you do it.** Sales demo script, onboarding checklist, refund policy, escalation path — playbooks are what let you hire without chaos.

  ## 4. Team Tips

  1. **First five hires decide the company:** lead engineer who has shipped multi-tenant systems, a designer who *thinks* in RTL (not translates into it), and an AE who has sold to Saudi SMB owners face-to-face. Compromise on seniority elsewhere, never on these.
  2. **Founder sells for the first 50 customers.** No exceptions. You cannot write the sales playbook you haven't lived, and investors can smell delegated-too-early sales.
  3. **Pay commissions transparently and instantly visible** — you sell commission software; your own AEs should see their numbers live in a dashboard. Dogfooding as culture.
  4. **Hire bilingual customer success before you think you need it** — CS hired after churn appears is firefighting; CS hired before is architecture.
  5. **Equity hygiene:** an ESOP pool (10–15%) created at incorporation, standard vesting for everyone including founders, and a one-page offer template. ⚖️
  6. **Engineers visit customers monthly.** One hour watching a receptionist fight the queue screen outperforms ten retro meetings.

  ## 5. Tech Stack Tips

  1. **Stack discipline:** Django REST Framework + PostgreSQL + Redis + Celery on the backend; SvelteKit (Svelte 5 runes) + Tailwind v4 on the frontend; `uv` for Python env/deps, npm for frontend. Resist every shiny detour — boring stacks ship.
  2. **Tenant isolation is non-negotiable at the database layer:** `organization_id` on every row, PostgreSQL row-level security enforced, and automated tests that *prove* tenant A can never read tenant B. One leak ends the company.
  3. **Money and stock are append-only:** double-entry ledger entries and stock movements are never updated or deleted — corrections are new entries. Auditors, ZATCA, and your own sanity depend on it.
  4. **State machines, not booleans:** bookings, payments, invoices, subscriptions each get explicit status enums with allowed-transition validation. Cascading boolean flags are where data corruption is born.
  5. **Concurrency at the database, not in Python:** exclusion constraints for booking overlaps, `select_for_update` on counters (ZATCA ICV, invoice sequences), idempotency keys on every mutating endpoint and every webhook consumer (Moyasar/Unifonic deliver at-least-once).
  6. **Kill N+1 queries before they kill demo day:** `select_related`/`prefetch_related` as code-review checklist items; query-count assertions in tests for every list endpoint.
  7. **Offline PWA rule:** offline devices may *queue* operations but never finalize money. Sync resolves with server-authoritative conflict policy for anything financial.
  8. **Partition the firehose tables** (analytics events, audit logs) monthly from day one — repartitioning a 200M-row table during a funding round is a story you don't want.
  9. **Staging environment with ZATCA sandbox + Moyasar test keys** mirroring production, and seed scripts that build a realistic demo tenant in one command — your sales team will live in it.

  ## 6. Marketing Tips

  1. **Case studies are the entire strategy in this market.** A filmed Arabic testimonial of a Riyadh salon owner saying "no-shows dropped 47%" outsells every feature page you will ever write. Manufacture these assets deliberately from your design partners.
  2. **Publish pricing openly.** Local competitors hide it; transparency converts the comparison-shopping owner and pre-qualifies your demos.
  3. **Own the Arabic search intent:** «نظام إدارة صالون», «برنامج حجوزات عيادات», «التوافق مع زاتكا المرحلة الثانية» — Arabic B2B SaaS content is a near-empty field; 12 months of weekly publishing makes you the default answer for years.
  4. **Snapchat and TikTok are B2B channels in KSA** — salon and clinic owners are heavy consumers there. Creative formula: real owner, real dashboard, one number, 20 seconds.
  5. **The demo is the close:** set up the prospect's actual services live in 20 minutes on a tablet, leave them in a 14-day trial with *their own data* already inside. Empty-trial conversion is a fraction of seeded-trial conversion.
  6. **Channel partners who already sit at the table:** accountants (ZATCA referrals), POS hardware resellers, business-setup consultancies. Pay 15–20% first-year revenue share and arm them with co-branded Arabic material.
  7. **Events with intent:** LEAP and Biban for pipeline, Seamless for partners. Book meetings *before* the event; the booth is the excuse, the calendar is the asset.
  8. **One metric per campaign.** If a campaign can't be judged by a single number (demos booked, trials started), don't run it.

  ## 7. Strategy Tips

  1. **Sequence beats breadth:** salons + clinics → ticketing/entertainment → enterprise → UAE. Every premature vertical splits your roadmap, your content, and your sales narrative.
  2. **Compliance → payments → AI is your value staircase.** Sell entry on compliance pain, expand revenue on payments, defend the account with AI insights nobody else can compute. Tell investors this staircase explicitly.
  3. **Make switching out painful and switching in painless:** free migration *into* Namaa; stored value (gift cards, packages, loyalty points) and historical analytics naturally anchor customers *in*. Never hold data hostage — lock-in through value, not hostage-taking, or PDPL and reputation will both bite.
  4. **Watch Glamera's payments moves and Fresha's pricing moves quarterly** — one is your local benchmark, the other your global price anchor. Differentiate on compliance depth and multi-branch operations, never on price.
  5. **Default to partner-led expansion outside KSA:** your own office in a new market is a Series-A decision; a reseller with local relationships is a this-quarter decision.
  6. **Say no in writing:** keep a public-internal "not doing now" list (custom development, white-labeling, hardware manufacturing). Focus is a document, not a feeling.
  7. **Build the Series-A metrics pack from month one** — NRR, cohort retention curves, CAC payback, payments volume — even if you never raise. The discipline compounds.

  ## 8. UI Design Tips

  1. **Design RTL-first, then mirror to LTR** — the reverse always leaks: misaligned icons, wrong chevrons, broken chart axes. Your design tool artboards should default to Arabic.
  2. **Role-based first screens:** owner sees money, receptionist sees today, cashier sees POS. Nobody should navigate to their job.
  3. **The three-click rule for daily actions:** book, sell, check-in — each reachable in ≤3 interactions, measured in usability tests with actual receptionists.
  4. **POS is touch-first and keyboard-free:** large targets (gloved/long-nailed hands are your literal users), sub-second search, the offline state always visible with a queued-operations counter.
  5. **Numbers before charts:** every dashboard tile leads with the figure and a trend arrow; the chart is supporting evidence, not the headline.
  6. **Reserve one color for money-good moments:** the gold accent appears only on payment success and goal achievement — it trains an emotional association with revenue.
  7. **Render the calendar culturally:** prayer-time bands, Ramadan hours, Hijri date display by preference — these details scream "built for us" in a demo more than any feature list.
  8. **Empty states sell:** every empty screen shows what success looks like with one obvious action («أضف أول خدمة») — onboarding is UI, not documentation.
  9. **Animation budget:** under 200ms, purposeful, never on operational hot paths; one celebratory moment per milestone is charm, two is noise.
  10. **Test with real users monthly:** one receptionist, one owner, one cashier, recorded screen sessions. Five usability sessions reveal 80% of the problems — schedule them as rituals, not events.

  ------

  *Keep this file beside the Master Documentation. Revisit quarterly; strike through what you've institutionalized.*