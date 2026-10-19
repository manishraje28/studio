# Studio — an autonomous AI agency you can watch work

> A team of AI agents (strategist, researcher, art director, copywriter, developer, QA) takes a small business from **brief to a live, distinctive website and launch kit in 72 hours**, for a fixed price, with every step visible on a live "studio floor". A human creative director signs off at two checkpoints.

**Status:** Validation + product spec v1 · 19 Oct 2026

---

## Part 1 — Validation

### 1.1 The problem
Small businesses are stuck between two bad options:
1. **Human agencies and freelancers:** expensive, slow and opaque, with a real chance of getting burned.
2. **AI website builders:** fast and cheap, but **generic**. Every plumber ends up looking like a VC-funded SaaS startup.

Nobody sells what the owner actually wants: **a site that looks like *their* business, delivered fast, at a known price, with nothing hidden.**

### 1.2 Evidence (gathered with Agent Reach + Exa)

**Agencies burn people:**
| Thread | Signal |
|---|---|
| [r/smallbusiness — "Project took 5x longer and I was invoiced 220% over what was quoted"](https://www.reddit.com/r/smallbusiness/comments/17nx9g5/project_took_5x_longer_and_i_was_invoiced_220/) | 121 pts, 206 comments. A $33.7k quote turned into a $74.3k invoice over 110 weeks. |
| [r/webdesign — "Are there any legitimate web design companies?"](https://www.reddit.com/r/webdesign/comments/1qtosac/as_a_small_business_owner_are_there_any/) (Feb 2026) | 145 comments. The owner said it *feels like a used car dealership*. |
| [r/ecommerce — "Paid almost 10K for a website we can't use"](https://www.reddit.com/r/ecommerce/comments/1e9txod/paid_almost_10k_for_a_website_we_cant_use_how_do/) | Tasks "technically done", but the quality was far below what was promised. |
| [r/smallbusiness — "How would you get your 10k back from a dodgy agency?"](https://www.reddit.com/r/smallbusiness/comments/1b8pm94/how_would_you_get_your_10k_back_from_a_dodgy/) | A branding agency vanished mid-project. |

**AI builders produce generic sites:**
| Thread | Signal |
|---|---|
| [r/ai_website_builder — "every startup looks like the same copy-paste template"](https://www.reddit.com/r/ai_website_builder/comments/1tgjevo/are_websites_made_from_ai_website_builders/) (May 2026) | *"Why does a plumber's website look like it's trying to raise venture capital?"* |
| [r/web_design — "AI web design is terrible"](https://www.reddit.com/r/web_design/comments/1t7o6fo/ai_web_design_is_terrible_need_help/) (May 2026) | Output is "technically fine" but has "no point of view". Good sites have *one or two strong custom ideas*. |
| [r/startups — "Do you still hire designers?"](https://www.reddit.com/r/startups/comments/1rdz0nz/do_you_actually_hire_designers_anymore_or_just/) (Feb 2026) | AI is fast for drafts, but the result is "generic or cartoonish, unprofessional slop". |

**Agencies are already moving to agents:**
| Thread | Signal |
|---|---|
| [r/agency — "Anyone built a fully agentic agency?"](https://www.reddit.com/r/agency/comments/1spxfde/any_agency_owners_thinking_of_or_have_already/) (Apr 2026) | A practitioner runs a per-client context folder, n8n, Claude Code and custom RAG. They say it is *not fully agentic yet*, and that "faster and cheaper" alone attracts bad clients. **Quality and outcome must be the positioning.** |
| [r/agency — productized AI services](https://www.reddit.com/r/agency/comments/1rmnt3i/anyone_doing_productized_service_with_something/) (Mar 2026) | *"Clients don't care about the AI, they just want the assets fast."* Revisions are where the margin is. |
| [r/agency — "Digital marketing agency came to the END"](https://www.reddit.com/r/agency/comments/1sx47tb/digital_marketing_agency_came_to_the_end/) (Apr 2026) | An agency replaced manual roles with agents, reported 70% growth and $15k a month saved. |

### 1.3 Market
- Businesses typically spend **$1k–$30k** on a website build, and **57% spend $501–$10k a year** on ongoing design ([WebFX 2026](https://www.webfx.com/web-design/pricing/)).
- The existing behaviour (paying agencies) is the demand. Studio competes on **price × speed × trust**, not by teaching people a new habit.

### 1.4 Competitors and the gap

| Player | Strength | Gap Studio exploits |
|---|---|---|
| Lovable, Bolt, v0 | You own the code | You must prompt and design yourself, and the output is generic |
| Framer AI | Best looks ([review](https://launchtoolsai.com/best/best-ai-website-builders-2026)) | DIY, frontend-only, forms not wired up |
| Wix, Durable | Instant | No code export, lock-in ([review](https://studioslate.com.au/blog/ai-website-builders-review)) |
| Human agencies | Taste, accountability | Slow, expensive, opaque |
| AI-assisted agencies | Speed internally | The client still can't see the process; they are still a black box |

**Studio's three differentiators:**
1. **Research-driven taste.** Agents study *this* business first: its reviews, competitors, local market, photos and voice. Only then do they design. An "anti-generic" critic agent rejects default SaaS aesthetics.
2. **Radical transparency.** A live studio floor shows every agent, task, draft and decision. You watch your agency work, which directly fixes the "used car dealership" feeling.
3. **Fixed outcome.** Fixed price, 72-hour delivery, the client owns the code on GitHub, and the site is deployed. Two revision rounds are included.

### 1.5 Risks
- **Taste is hard:** mitigated by the critic agent, a reference library and a human creative director gate.
- **Model cost per project:** about $5–15 of Claude usage per project at current pricing (estimate). It must stay under 5% of the price.
- **Scope creep:** fixed packages, with a scope agent that refuses out-of-scope requests and quotes them as add-ons.
- **Hallucinated facts in copy:** every business claim needs a source (the intake form, a review, or a document the client uploaded).

---

## Part 2 — Product spec

### 2.1 Personas
- **Meera, café owner:** wants a site that feels like her café, not a template. Budget ₹25–60k.
- **Arjun, solo consultant:** needs a credible brand and site this week for a pitch.
- **Later: agency owners** who white-label Studio as their delivery engine (B2B2C).

### 2.2 Packages
| Package | Deliverables | Price (indicative) |
|---|---|---|
| **Launch** | Brand mini-kit (logo, palette, type), 5-page site, copy, SEO basics, deployment | ₹24,999 / $399 |
| **Launch+** | + booking or forms backend, blog CMS, Google Business profile copy, 10 social posts | ₹49,999 / $799 |
| **Care** | Monthly updates, SEO report, new pages on request | ₹2,999 / $49 a month |

### 2.3 The agent team

| Agent | Role | Tools | Output |
|---|---|---|---|
| **Account manager** | Talks to the client, runs the brief interview, handles revisions, enforces scope | chat, voice notes, calendar | Signed brief |
| **Researcher** | Reads the client's existing site, Google reviews, competitors, Instagram and local market | web fetch, search, image analysis | Research dossier with citations |
| **Strategist** | Positioning, audience, sitemap, page goals, CTAs | dossier, frameworks | Strategy doc |
| **Art director** | Moodboard, palette, type, layout direction; picks the **one or two signature ideas** | image generation, reference library, palette validator | Style tiles + design tokens |
| **Copywriter** | Voice and tone, page copy; every claim sourced | brief, dossier | Copy deck |
| **Developer** | Builds a Next.js site from design tokens and copy; wires forms, CMS and analytics | code sandbox, component library, git | Repo + preview URL |
| **QA / critic** | Lighthouse, accessibility (axe), broken links, mobile screenshots, and an **anti-generic score** against a rubric | Playwright, Lighthouse, vision model | QA report; sends work back to the agent responsible |
| **Producer** (orchestrator) | Plans the job DAG, assigns tasks, tracks budget and deadline, escalates to a human | task graph, cost meter | Timeline, status |

**Human checkpoints:** (1) the creative director approves the art direction, and (2) the client approves the preview before launch. Everything else runs on its own.

### 2.4 Project lifecycle
```
Brief (client chat, 15 min)
 → Research (Researcher)            ── live on studio floor
 → Strategy + sitemap (Strategist)
 → Art direction (Art Director)     ── ✋ Creative-director gate
 → Copy ∥ Build (Copywriter, Developer, in parallel)
 → QA loop (Critic ↔ Dev/Copy until score ≥ threshold)
 → Client preview                   ── ✋ Client approval, 2 revision rounds
 → Deploy (Vercel/Netlify) + GitHub handover + launch kit
```

### 2.5 Key product surfaces
1. **Landing site:** a 3D hero showing the studio floor as an isometric office where agent avatars move between desks as work flows (React Three Fiber).
2. **Client portal:**
   - **Studio floor:** a live view of agent activity, the current task, artifacts and the timeline.
   - **Artifact library:** dossier, strategy, style tiles, copy, preview link.
   - **Feedback:** comment directly on the preview (pin on element), and the Account manager turns comments into tasks.
   - Billing, deliverables, download repo.
3. **Ops console** (internal / creative director): queue, approval gates, cost per project, agent traces and replays, quality scores.
4. **Agency mode** (v2): white-label portal for agencies.

### 2.6 Architecture
```
Next.js 15 (landing + client portal + ops)  ◄── WebSocket (live studio floor)
          │ tRPC/REST
          ▼
   API (FastAPI)  ── Auth (Clerk/Auth.js), Stripe/Razorpay billing
          │
          ├─► Orchestrator (Producer) ── job DAG in Postgres, durable steps (Temporal or Inngest)
          │       └─► Agent workers (Claude API, tool use, prompt caching)
          │             tools: web fetch/search, image gen, code sandbox (E2B/Docker),
          │                    Playwright + Lighthouse, git, deploy API
          ├─► Postgres + pgvector  (projects, tasks, artifacts, embeddings of refs)
          ├─► Redis  (pub/sub for live events, rate limits)
          └─► Object storage (R2/S3)  (images, screenshots, builds)
```

| Layer | Choice |
|---|---|
| Frontend | Next.js 15, TypeScript, Tailwind, shadcn/ui, React Three Fiber + drei, Framer Motion |
| Backend | FastAPI (Python), Pydantic, SQLAlchemy |
| Orchestration | Temporal or Inngest for durable multi-day jobs with retries and human-wait steps |
| AI | `claude-opus-5-5` (strategy, art direction, critique), `claude-sonnet-5-5` (copy, code), `claude-haiku-5-5` (routing, summaries) |
| Code execution | Isolated sandbox per project (E2B or Docker), generated sites built from a curated component kit + design tokens |
| QA | Playwright screenshots, Lighthouse CI, axe-core, vision-model critique |
| Deploy | Vercel API (client site), GitHub App (repo handover) |
| Payments | Razorpay (India) + Stripe (global) |
| Observability | OpenTelemetry traces per agent step, cost metering, Sentry |

### 2.7 Data model
`client` · `project` (package, status, deadline, budget_tokens) · `brief` · `task` (agent, deps, status, attempt, cost) · `artifact` (type, version, url, source_task) · `approval` (gate, actor, decision, notes) · `feedback` (preview pin, text → task) · `agent_event` (stream to studio floor) · `quality_score` (lighthouse, a11y, anti_generic, rubric json) · `deployment`.

### 2.8 Guardrails
- Every agent gets only its own tools (the copywriter can't deploy; the developer can't email clients).
- Budget caps per project and per agent, with automatic escalation when exceeded.
- Client-supplied content and scraped web content are data, never instructions (prompt-injection defence).
- Image licensing: generated images or client-owned photos only, no scraped images.
- Every factual claim in the copy links back to its source in the dossier.

### 2.9 Success metrics
- Brief-to-live time (target ≤ 72 hours).
- First-preview approval rate (target ≥ 60%), average revision rounds ≤ 1.5.
- Anti-generic score, measured as blind-test preference against Lovable/Framer output.
- Gross margin per project (target ≥ 85%).
- NPS, and the share of Launch clients who convert to Care.

### 2.10 Build plan (8 weeks)
| Week | Deliverable |
|---|---|
| 1 | Monorepo, auth, DB schema, CI, Docker; orchestrator skeleton with a fake agent |
| 2 | Researcher + Strategist agents, artifact store, live event stream |
| 3 | Art director: design tokens, style tiles, reference library, palette validator |
| 4 | Copywriter + Developer agents, component kit, code sandbox, preview deploys |
| 5 | QA/critic loop (Playwright, Lighthouse, vision rubric), revision routing |
| 6 | Client portal: studio floor (live), artifacts, pin feedback, approvals |
| 7 | 3D landing page, payments, ops console, cost metering |
| 8 | Run 3 real projects end-to-end (friends' businesses), case studies, demo video, deploy |
