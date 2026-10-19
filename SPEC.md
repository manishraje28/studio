# Munshi — the AI compliance clerk for Indian small businesses

> *Munshi* (मुंशी): the clerk who kept a business's books, records and deadlines. We're building the AI version, and it lives on WhatsApp.

**Status:** Validation + product spec v1 · 19 Oct 2026

---

## Part 1 — Validation

### 1.1 The problem in one line
Small business owners don't fail at compliance because the rules are hard. They fail because the **coordination** is chaos. Invoices sit in WhatsApp, bank statements sit in email, the CA has 30–50 clients, and nobody owns the deadline.

### 1.2 Evidence (real posts, gathered with Agent Reach + Exa)

| Source | What it says |
|---|---|
| [r/IndiaBusiness — "We thought our CA was handling it"](https://www.reddit.com/r/IndiaBusiness/comments/1qgwr3y/we_thought_our_ca_was_handling_it_the_costliest/) (Jan 2026) | GST monthly, TDS quarterly, ROC yearly, HR on top: *"What usually breaks isn't expertise — it's coordination."* |
| [r/IndiaBusiness — "Small business compliance and bookkeeping in India is broken"](https://www.reddit.com/r/IndiaBusiness/comments/1tgrbhp/small_business_compliance_and_bookkeeping_in/) (May 2026) | Invoices on WhatsApp, statements on email, bills missing. *"By the time everything reaches the CA, it's already the 17th."* The results are late filings, missed ITC claims and penalties. |
| [r/smallbusiness — "How do you handle all the paperwork/compliances without getting mad?"](https://www.reddit.com/r/smallbusiness/comments/1qgcj24/how_do_you_handle_all_the_paperworkcompliances/) (Jan 2026, Indian OP) | *"It's not even the work, it's the constant mental load."* The top reply: nobody has a real system, just "organized panic". |
| [r/StartUpIndia — "My accountant failed to file GST…"](https://www.reddit.com/r/StartUpIndia/comments/1hlv06w/first_time_founder_my_accountant_failed_to_file/) (41 pts, 38 comments) | A first-time founder got burned on a missed nil return. |
| [r/IndiaTax — "Got a penalty of 50k on GST portal"](https://www.reddit.com/r/IndiaTax/comments/1mp0ait/got_a_penalty_of_50k_on_gst_portal/) | A ₹50k penalty for a late nil GSTR-3B, discovered a year later. |
| [r/LegalAdviceIndia — show cause notice u/s 125](https://www.reddit.com/r/LegalAdviceIndia/comments/1w0sx77/got_a_show_cause_notice_us_125_for_non_filing_of/) (Aug 2026) | The owner had no portal access and missed the notice reply date by a month. |
| [r/AI_Agents — "What AI agent would make your life easier in 2026?"](https://www.reddit.com/r/AI_Agents/comments/1qlar98/what_ai_agent_would_actually_make_your_life/) | The top comment (9 pts): *"something that handles life admin… it never really works right yet."* |

**Recurring pains:** (1) not knowing which deadlines apply to me, (2) chasing documents for the CA, (3) panic when a notice arrives, (4) losing input tax credit (ITC) because purchase bills don't match GSTR-2B, (5) no visibility into what the CA has actually filed.

### 1.3 Market size
- **1.70 crore** registered GST taxpayers ([GSTN](https://www.gstn.org.in/), 30 Sep 2026).
- **~9.9 crore** formalised MSMEs, 99% of them micro ([MSME Dashboard](https://dashboard.msme.gov.in/), 18 Oct 2026).
- Late fees alone came to **₹4,172 cr** in the first 19 months of GST ([Indian Express](https://indianexpress.com/article/business/economy/delayed-filing-of-returns-rs-4172-crore-late-fee-collected-since-gst-launch-5579019/)) and roughly **₹200 cr a month** in 2019 ([TaxGuru / RTI](https://taxguru.in/goods-and-service-tax/govt-collects-1898-crore-nine-months-gst-late-fees.html)). This is money owners pay purely for being disorganised.
- **New urgency:** returns are now **barred 3 years after their due date** ([GST portal FAQ](https://tutorial.gst.gov.in/userguide/returns/FAQs_application_Unbarring.htm)). Old gaps can't be quietly fixed later any more.

### 1.4 Competitors and the gap

| Player | What they are | Why they don't solve this |
|---|---|---|
| ClearTax, Zoho Books, Tally | Accounting / filing software | Built for the person *doing* the books. Owners don't open them. |
| IndiaFilings, Vakilsearch | Done-for-you services | Many public complaints about missed filings and slow response ([consumer complaints](https://www.consumercomplaints.in/bycompany/india-filings-a423519.html), [reviews](https://www.biznod.com/review.php/legal-and-government/tax-and-compliance/indiafilings/)). |
| QwikBills, Hisabkitab, Fortax | AI accounting suites (2025–26) | They want you to **replace** your books. The agents are mostly payment chasing or "coming soon". |

**Munshi's wedge:** don't replace Tally or the CA. Be the **agentic coordination layer** between the owner, the CA and the government portal, working through WhatsApp, which the owner already lives in. The owner never has to learn a new app.

### 1.5 Risks and honest limits
- **Filing on the portal** needs a GSP licence or ASP partnership. For the MVP, the CA files; Munshi prepares, reminds, reconciles and tracks status. Filing via GSP API comes in v2.
- **Liability:** Munshi never gives a final legal or tax position. Every draft reply to a notice goes to a CA for approval (human-in-the-loop by design).
- **Data trust:** financial documents are sensitive. We need DPDP Act compliance, encryption at rest and per-tenant isolation from day 1.
- **Deadlines change** through CBIC notifications. The rule engine must be versioned data, not prompts.

---

## Part 2 — Product spec

### 2.1 Personas
1. **Ravi, owner** of a 6-person trading firm in Pune. Not a regular Tally user. WhatsApp all day. Pays a CA ₹2–5k a month.
2. **Priya, CA** with 40 SME clients. Spends the 10th–20th of every month chasing documents.

### 2.2 Core loop
```
Owner forwards bills / statements on WhatsApp
   → Intake agent extracts + files them
   → Obligation engine knows what's due & what's missing
   → Chaser agent nudges owner (Hindi/English/Marathi) before CA cutoff
   → CA cockpit shows "ready to file" clients
   → Status confirmed → owner gets a ✅ and a monthly health score
```

### 2.3 Agents (each one is a tool-using Claude agent with bounded permissions)

| Agent | Job | Tools | Autonomy |
|---|---|---|---|
| **Intake** | Classify each incoming document (purchase invoice, sales invoice, bank statement, notice, other) and extract GSTIN, invoice no., date, taxable value and tax heads | vision/OCR, GSTIN validator, document store | Auto; asks the owner when confidence is low |
| **Obligation engine** (deterministic, *not* an LLM) | Work out which returns apply from profile + turnover + state (GSTR-1/IFF, 3B, QRMP, CMP-08, TDS, ROC, PT) and their due dates | versioned rules table | Auto |
| **Chaser** | Plan which documents are missing per deadline, and send escalating reminders by voice note or text | WhatsApp send, schedule, obligation state | Auto within quiet hours and a rate limit |
| **Reconciler** | Match the purchase register against the GSTR-2B the CA uploads, flag ITC at risk in rupees, and draft the vendor follow-up message | matcher, WhatsApp draft | Drafts only; the owner approves sends |
| **Notice agent** | Read a GST notice PDF, find the section, due date and demand, explain it in plain language, gather the evidence and draft a reply | RAG over CGST Act + circulars, case docs | **Draft only → CA approves** |
| **Supervisor** | Route messages, keep per-business memory, write a full audit log of every agent action | all of the above | — |

### 2.4 MVP features (v1, about 8 weeks)
1. WhatsApp onboarding: GSTIN in, auto-filled business profile, compliance calendar out.
2. Document intake via WhatsApp with a searchable document vault.
3. Deadline calendar plus the Chaser agent.
4. Notice explainer with a draft reply and the CA approval flow.
5. ITC reconciliation from an uploaded GSTR-2B (JSON/Excel) showing ₹ at risk.
6. **CA cockpit** (web): all clients in one view, readiness per deadline, one-click document export.
7. **Owner dashboard** (web + WhatsApp summary): health score, upcoming deadlines, money at risk.
8. Landing site with a 3D hero (an animated "paper storm turns into an ordered ledger" scene).

**v2:** GSP filing integration, Tally/Zoho sync, TDS and ROC, voice calls, payroll compliance, a marketplace matching owners to CAs.

### 2.5 Architecture

```
            WhatsApp Cloud API ──webhook──┐
                                          ▼
 Next.js 15 (web) ──REST/tRPC──►  API gateway (FastAPI)
  • 3D landing (R3F)                    │
  • Owner dashboard                     ├─► Agent service (Claude API, tool use)
  • CA cockpit                          │     supervisor + 5 agents
                                        ├─► Job queue (Redis + Arq workers)
                                        │     OCR, reminders, recon, schedules
                                        ├─► Postgres (+ pgvector)
                                        │     tenants, docs, obligations, audit
                                        └─► Object storage (R2/S3, encrypted)
```

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js 15, TypeScript, Tailwind, shadcn/ui, React Three Fiber, Framer Motion | Production standard; good 3D support |
| Backend | Python FastAPI, Pydantic, SQLAlchemy | Best ecosystem for documents and AI |
| AI | Claude (`claude-opus-5-5` for notices and reasoning, `claude-haiku-5-5` for classification), tool use, prompt caching | Strong on documents, long context, cheap at volume |
| Retrieval | pgvector over the CGST Act, rules, circulars and notifications | One database, citations included |
| Jobs | Redis + Arq | Scheduled reminders, async OCR |
| Messaging | Meta WhatsApp Cloud API (sandbox for dev) | Where users already are |
| Auth | Phone OTP for owners, email + 2FA for CAs; role-based access per tenant | |
| Infra | Docker Compose locally, then Fly.io/Render + Neon + Upstash; GitHub Actions CI | Cheap, real deployment |
| Observability | OpenTelemetry, Sentry, an agent trace viewer in admin | Shows agent reasoning; great for demos |

### 2.6 Core data model
`tenant` (business, GSTIN, state, scheme, turnover band) · `user` (role: owner/staff/ca) · `ca_client_link` · `document` (type, extracted JSON, confidence, source msg) · `obligation` (return type, period, due date, status, rule_version) · `requirement` (obligation ← documents needed) · `notice` (section, demand, reply due, draft, approval state) · `recon_run` / `recon_item` · `agent_action` (agent, tool, input, output, approved_by — the audit log) · `message` (WhatsApp in/out).

### 2.7 Guardrails
- Tax numbers come from deterministic code. The LLM explains them but never invents them.
- Every outbound message has an approval policy (auto / owner / CA) per agent.
- Every legal claim in a notice draft must cite a section or circular.
- Prompt-injection defence: content from documents is treated as data, and tools are scoped per agent.
- PII is encrypted, data is deleted on request (DPDP), tenants are isolated with Postgres RLS.

### 2.8 Success metrics
- Share of obligations filed on time (target 98%+, against a baseline of about 70% in user interviews).
- ₹ ITC recovered per business per month.
- Number of days before the CA cutoff by which documents are complete.
- Time saved for the CA per client per month.

### 2.9 Business model
- Owner: free calendar and reminders → **₹499 a month** Pro (intake, recon, notices).
- CA: **₹199 per client per month** cockpit. The CA is the distribution channel, since one CA brings 40 businesses.

### 2.10 Build plan

| Week | Deliverable |
|---|---|
| 1 | Monorepo, Docker, DB schema, auth, CI |
| 2 | Obligation rules engine + tests, calendar API |
| 3 | WhatsApp webhook, Intake agent, document vault |
| 4 | Chaser agent + scheduler, owner dashboard |
| 5 | Notice agent with RAG over the CGST Act, approval flow |
| 6 | Reconciler, CA cockpit |
| 7 | 3D landing page, polish, seed demo data |
| 8 | Deploy, load test, security review, demo video + pitch deck |
