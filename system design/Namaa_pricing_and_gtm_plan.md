# Namaa — Pricing Architecture & 24-Month Go-To-Market Plan (KSA / GCC)

------

# Part 1 — Pricing Architecture

## 1.1 Strategic Corrections Before the Numbers

Your two documents currently contradict each other: `Namaa_docs.md` introduces a "Starter Plan" (the table is truncated and the price cell is empty), while the Enterprise Profile explicitly rejects low-price tiers. Resolve this deliberately — both extremes lose money in KSA:

- **No entry tier** = you hand the entire long tail of salons and solo clinics to Fresha (free/commission model) and Glamera, and you lose the upgrade pipeline that feeds your Growth tier.
- **Cheap flagship tiers** = you can't afford field sales, Arabic onboarding, and an account manager culture — which is exactly how Glamera competes locally.

The fix: a **self-serve entry tier as an acquisition engine** (no human sales cost) + premium tiers that carry the field-sales motion. Also: **stop selling ZATCA Phase 2 as a 450 SAR/branch/month add-on.** Phase 2 integration is a legal obligation in KSA and competitors increasingly bundle it; charging heavily for compliance reads as a penalty and will be the #1 deal-killer objection. Include it from the Growth tier up and monetize AI, WhatsApp, and payments instead.

## 1.2 Subscription Tiers (SAR, VAT-exclusive)

|                                                | **انطلاقة Launch** | **نمو Growth**      | **توسع Expansion**          | **مؤسسات Enterprise**             |
| ---------------------------------------------- | ------------------ | ------------------- | --------------------------- | --------------------------------- |
| Monthly (billed annually)                      | **449**            | **1,200**           | **3,500**                   | Custom                            |
| Month-to-month price                           | 549                | 1,450               | 4,200                       | —                                 |
| Annual contract value                          | 5,388              | 14,400              | 42,000                      | from **95,000/yr**, multi-year    |
| Branches                                       | 1                  | 1                   | up to 5 (+600/mo per extra) | Unlimited                         |
| Staff accounts                                 | 5                  | 15                  | Unlimited                   | Unlimited                         |
| Bookings, POS, invoicing, CRM                  | ✔                  | ✔                   | ✔                           | ✔                                 |
| ZATCA Phase 2 live integration                 | +150/mo            | **Included**        | **Included**                | Included                          |
| Loyalty, ticketing engine, advanced analytics  | —                  | Loyalty only        | ✔                           | ✔                                 |
| AI Pack (LTV, churn, demand forecast, content) | —                  | +500/mo             | +500/mo                     | Included                          |
| Official WhatsApp channel                      | —                  | +300/mo + usage     | +300/mo + usage             | Included + usage                  |
| Support                                        | Self-serve + chat  | Priority chat       | Dedicated CSM               | Account manager, SLA, isolated DB |
| Sales motion                                   | Self-serve signup  | Inside sales / demo | Field sales                 | Founder/enterprise sales          |

Design logic per tier:

- **Launch (449)** exists to make "free Fresha" a false economy: it's priced near the cost of one no-show per week, captures solo clinics/barbershops self-serve, and its hard limits (1 branch, 5 staff, no loyalty/ticketing) create natural upgrade pressure. No human touches these deals — keep CAC near zero.
- **Growth (1,200)** is your volume engine and matches your existing positioning. Raised staff cap from 5 → 15: at 1,200/mo a 5-staff cap is the most common objection a salon owner in Riyadh will raise, and seats cost you nothing.
- **Expansion (3,500)** targets 2–5 branch chains, your highest-LTV mainstream segment. The 600/branch overflow fee is good — keep it; it converts naturally into Enterprise conversations at branch 8–10.
- **Enterprise (95k+)** unchanged, but anchor it on isolated infrastructure, custom integrations, and SLA — not features.

## 1.3 Revenue Layers Beyond Subscriptions (the real path to high ARPU)

1. **Payments margin (the biggest one).** Follow Glamera's playbook: become the payment layer, not just the software. Negotiate wholesale rates with Moyasar and resell with a **0.4–0.8% platform margin** on card volume (mada/Visa/Apple Pay). A single mid-size salon doing 150k SAR/month in card volume yields 600–1,200 SAR/month in margin — silently doubling its subscription value. Long-term, pursue SOFTPOS/Saudi Payments authorization.
2. **Messaging margin.** Re-bill Unifonic SMS/WhatsApp with a 20–25% markup, metered through the `UsageRecord` entity. Reminder volume scales with the customer's success, so this revenue is self-growing.
3. **Onboarding & migration fees.** 1,500 SAR (Growth), 4,000 SAR (Expansion), 15,000+ (Enterprise) — covering data migration from spreadsheets/Glamera/Fresha, staff training in Arabic, and ZATCA device onboarding. This filters unserious buyers and funds your CS team.
4. **AI Pack (500/mo)** stays an add-on — it's your differentiation story and demos beautifully, but never gate core operations behind it.
5. **Annual-first billing.** Quote annual prices by default with the monthly price shown as the penalty option (~20% premium). Annual prepay in SAR is normal for KSA B2B and transforms your cash flow.

## 1.4 Reality-Check Math (so the "millions" goal is a plan, not a slogan)

ARR needed for USD 1M ≈ **3.75M SAR**. Illustrative mixes that reach it:

| Mix             | Launch | Growth | Expansion | Enterprise | Subscription ARR | + Payments/messaging/add-ons (~30%) |
| --------------- | ------ | ------ | --------- | ---------- | ---------------- | ----------------------------------- |
| Month 12 target | 120    | 90     | 12        | 1          | ~2.6M SAR        | **~3.4M SAR**                       |
| Month 24 target | 350    | 280    | 45        | 5          | ~8.7M SAR        | **~11.3M SAR (~USD 3M)**            |

To hit month-12, you need roughly **20–25 net new paying customers/month** from month 4 — that's the demand the marketing plan below is sized for. Guard the two metrics that decide everything in this market: logo churn < 2%/month and NRR > 110% (branch expansion + add-ons do the NRR work for you).

------

# Part 2 — 24-Month Marketing & GTM Plan (KSA-first)

## Phase 0 — Foundation & Design Partners (Months 0–3)

**Goal: 12–15 live design partners, ZATCA certification, proof assets. Spend: 40–60k SAR.**

- **Pick two beachhead verticals, not six.** Recommended: **multi-chair salons/barbershops** (highest density, fastest sales cycle) and **dental/derma clinics** (highest willingness to pay, ZATCA + medical-notes pain). Entertainment/ticketing waits until Phase 2 — focus beats breadth.
- Recruit 12–15 design partners in Riyadh and Jeddah: free for 6 months in exchange for weekly feedback, a logo on your site, and a filmed Arabic video testimonial with real numbers ("no-shows down 47%"). These case studies are the single highest-ROI marketing asset in this market — Saudi SMB owners buy on peer proof, not feature lists.
- Ship the trust layer: Arabic-first website (RTL native, not translated), فاتورة/ZATCA compliance badge, CR + VAT registration visible, sa. domain, Google Business profile, and pricing published openly (most local competitors hide pricing — transparency is a differentiator).
- Complete ZATCA Phase 2 compliance solution certification and document it loudly.
- Found-led channels: LinkedIn (B2B credibility, English+Arabic), X/Twitter (Saudi tech community), and start a TikTok/Snapchat presence early — Snapchat reach in KSA is enormous and salon owners are consumers there too.
- Register with **Monsha'at** ecosystem and apply for relevant programs (Tomoh, accelerators); explore **CODE/MCIT** tech community visibility.

## Phase 1 — Public Launch & Repeatable Sales (Months 4–9)

**Goal: 60–100 paying customers, CAC payback < 9 months. Spend: 60–100k SAR/month.**

- **Launch moment:** time it to **LEAP** (Riyadh, ~Feb) or **Seamless KSA** — book a small stand or piggyback on a partner's; collect demos on-site. Add **Biban** (Monsha'at's SME festival) — it is exactly your buyer in one building.
- **Paid acquisition (Arabic-first):**
  - Google Ads on high-intent Arabic keywords: «نظام إدارة صالون», «برنامج حجوزات عيادة», «نظام فوترة زاتكا للصالونات», plus competitor terms (Glamera, Fresha alternatives).
  - Meta + Snapchat + TikTok: short owner-testimonial videos targeted at business-owner interest segments in Riyadh/Jeddah/Dammam. Creative formula: real owner, real dashboard, one number ("استرجعت ٣٠ ساعة شهرياً").
- **Field + inside sales motion:** 2 Arabic-speaking SDR/AEs doing neighborhood sweeps of salon clusters and clinic districts (Olaya, Al Rawdah, Tahlia…). The demo IS the close in this market — bring a tablet, set up their actual services live in 20 minutes, leave them on a 14-day trial with their own data already inside.
- **Partnerships as channels:**
  - **Moyasar** co-marketing (you drive them volume).
  - POS hardware resellers and business-setup consultancies (they meet every new salon/clinic at incorporation) — pay 15–20% first-year revenue share.
  - Accountants/bookkeeping firms: ZATCA Phase 2 makes them your perfect referrer.
- **Referral program:** one free month per referred paying customer, both sides. Salon owners talk to each other constantly; formalize it.
- **PR:** Arabic tech/business media (عالم التقنية, Argaam business coverage, رواد الأعمال) with the "Saudi-built, Vision-2030-aligned operations platform" angle.
- KPIs: 150–250 demos/quarter, 30%+ demo→paid, churn < 3%/mo (early), 8+ published case studies.

## Phase 2 — Vertical Depth & Multi-Branch Dominance (Months 10–18)

**Goal: 250–400 customers, NRR > 110%, Expansion tier = 30%+ of new ARR. Spend: 100–150k SAR/month.**

- **Launch the ticketing/entertainment vertical now**, with the events engine as the hero — target padel clubs, kids' entertainment centers, and workshop studios riding the KSA entertainment boom.
- **ABM motion for chains:** build a named list of every 3–15 branch salon/clinic group in KSA (~commercial registry + Google Maps scraping + Instagram); run founder-level outbound with a custom ROI sheet per chain. These deals fund everything.
- **Content moat (Arabic SEO):** publish the definitive Arabic guides — "دليل التوافق مع المرحلة الثانية من زاتكا للعيادات", salon profitability calculators, no-show cost calculator tools (interactive, lead-gated). Arabic B2B SaaS content is a near-empty field; 12 months of consistent publishing makes you the default answer.
- **YouTube + webinars:** monthly Arabic webinar ("كيف تدير ٥ فروع من جوالك") and full product walkthroughs — these compound and de-load your sales team.
- **Community:** a private WhatsApp/Telegram group for owner-customers; run a quarterly "Namaa Majlis" dinner in Riyadh and Jeddah for customers + prospects. In KSA, the majlis closes more enterprise deals than any ad.
- **Customer marketing:** quarterly business reviews for Expansion tier showing their own numbers (revenue lift, no-show reduction) — this drives the add-on attach rate and referenceability.
- Geographic depth: dedicated coverage of Dammam/Khobar; evaluate Makkah/Madinah seasonal-business plays (Hajj/Umrah-adjacent services have unique scheduling needs your engine handles).

## Phase 3 — GCC Expansion & Enterprise (Months 19–24)

**Goal: 600+ customers, 8–12M SAR ARR run rate, first non-KSA market live. Spend: 150–200k SAR/month.**

- **First expansion market: UAE** (no language change, easy company setup, FTA e-invoicing arriving — your ZATCA muscle transfers). Enter via 2–3 reseller/implementation partners rather than your own office; adapt VAT/compliance layer first.
- **Qatar and Kuwait** via the same partner-led model in months 21–24; Bahrain/Oman opportunistically.
- **Enterprise push:** hire one enterprise AE; target hospitality groups, franchise operators, and healthcare groups with the isolated-infrastructure + SLA + custom-integration story. 5 enterprise logos ≈ 0.5M+ SAR ARR and brand gravity.
- **Brand campaign:** by now you have 20+ filmed success stories — run an awareness layer ("النظام السعودي لإدارة أعمال الخدمات") across LinkedIn/Snapchat/YouTube, plus airport/event presence at LEAP year 3.
- **Strategic positioning:** package your traction (NRR, payments volume, GCC footprint) as a Series A narrative even if you don't raise — it disciplines the metrics and opens partnership doors (banks, telcos like stc business who bundle SaaS for SMEs — a major distribution channel to pursue this phase).

## Budget & Team Shape Across 24 Months

|                               | Mo 0–3                        | Mo 4–9                            | Mo 10–18                                        | Mo 19–24                           |
| ----------------------------- | ----------------------------- | --------------------------------- | ----------------------------------------------- | ---------------------------------- |
| Monthly marketing+sales spend | 15–20k                        | 60–100k                           | 100–150k                                        | 150–200k SAR                       |
| Split                         | 80% content/brand/assets      | 50% paid / 30% sales / 20% events | 35% paid / 35% sales / 20% content / 10% events | + partner enablement               |
| Team                          | Founders + 1 content/designer | +2 AE/SDR, +1 CS                  | +1 marketer, +2 sales, +2 CS                    | +1 enterprise AE, +partner manager |

## The Five Numbers to Review Every Monday

1. New paying customers this week (target ramps 3 → 6 → 10/week across phases)
2. Demo → paid conversion (≥ 30%)
3. Monthly logo churn (< 2% by month 12 — in this segment churn is death; over-invest in onboarding)
4. NRR (> 110% — branches + WhatsApp + AI + payments margin)
5. CAC payback (< 9 months blended; Launch tier must stay near-zero CAC)