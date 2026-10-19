"use client";

import dynamic from "next/dynamic";
import AnimatedContent from "@/components/AnimatedContent";
import RotatingText from "@/components/RotatingText";
import ScrollVelocity from "@/components/ScrollVelocity";
import SplitText from "@/components/SplitText";
import { Header, Footer } from "@/components/site/Chrome";
import { TEAM } from "@/lib/team";

const Diorama = dynamic(() => import("@/components/studio/Diorama"), {
  ssr: false,
  loading: () => <div className="grid h-full place-items-center mono">Opening the studio</div>,
});

const Arrow = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
    <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.8" />
  </svg>
);
const Tick = () => (
  <svg viewBox="0 0 18 18" width="18" height="18" fill="none" stroke="var(--accent)" strokeWidth="2" className="mt-1 flex-none" aria-hidden>
    <path d="M4 9.5l3 3 7-7" />
  </svg>
);

const Reveal = ({ children, delay = 0, className }: { children: React.ReactNode; delay?: number; className?: string }) => (
  <AnimatedContent distance={36} duration={0.8} ease="power3.out" delay={delay} className={className}>
    {children}
  </AnimatedContent>
);

function SectionHead({ title, text }: { title: string; text: string }) {
  return (
    <div className="mb-14 flex flex-wrap items-end justify-between gap-x-10 gap-y-6">
      <SplitText text={title} tag="h2" splitType="words" delay={40} duration={0.7} mask={false}
        className="max-w-[680px] text-[clamp(32px,4vw,54px)] !leading-[1.12]" textAlign="left" />
      <Reveal className="max-w-[380px]"><p className="text-[var(--muted)]">{text}</p></Reveal>
    </div>
  );
}

const FLOOR = [
  { s: "done", who: "Researcher", what: "Read the Google reviews and three nearby cafés. Customers mention filter coffee, the reading corner and slow weekend mornings.", at: "Day 1 · 10:40" },
  { s: "done", who: "Strategist", what: "Five pages: Home, Menu, Space, Events, Visit. Main action: reserve a table for the weekend.", at: "Day 1 · 13:15" },
  { s: "done", who: "Art director", what: "Roasted brown, steamed milk and brass. Serif headings. Signature idea: the menu set like a library card.", at: "Day 1 · 17:30" },
  { s: "done", who: "Creative director (human)", what: "Approved the direction with one note: use the café's own photos only.", at: "Day 2 · 09:05" },
  { s: "live", who: "Developer", what: "Building the Menu page from the approved copy.", at: "Now" },
  { s: "todo", who: "QA critic", what: "Next: mobile screenshots, speed, accessibility and broken link checks.", at: "Queued" },
];

const PLANS = [
  { name: "Launch", price: "₹24,999", unit: "", note: "A complete small business site.", items: ["Up to 5 pages", "Logo, palette and type", "Copy written for you", "Contact form and Google Maps", "Domain setup and deployment", "2 revision rounds"], featured: false },
  { name: "Launch plus", price: "₹49,999", unit: "", note: "For bookings, enquiries and a blog.", items: ["Everything in Launch", "Up to 10 pages", "Booking or enquiry system", "Blog you can edit yourself", "Google Business profile text", "10 social media posts"], featured: true },
  { name: "Care", price: "₹2,999", unit: " / month", note: "Keep the site current after launch.", items: ["Small updates every month", "New page on request", "Monthly speed and SEO check", "Security updates"], featured: false },
];

const FAQ = [
  ["Will my site look like every other AI website?", "No. The agents start from research about your business, and a critic agent rejects layouts that look like a generic template. A human creative director signs off the direction."],
  ["Do I need to know anything technical?", "No. You answer questions in a chat, review a preview link and leave comments on it. We handle the domain and deployment."],
  ["What if I do not like the first version?", "You get two revision rounds. Each comment becomes a task for the agent responsible, and you can see it being worked on."],
  ["Which photos do you use?", "Your own photos. We do not use AI generated photos of people or fake product shots."],
  ["What happens to my data?", "Your brief and files are used only for your project. The privacy policy explains what we keep and how to ask us to delete it."],
];

const GETS = [
  { t: "A live website", d: "Up to 5 pages, deployed on your domain, fast on mobile.", i: <><rect x="3" y="4" width="18" height="14" rx="2" /><path d="M3 8h18M8 21h8" /></> },
  { t: "The source code", d: "A GitHub repository in your name. No lock-in and no platform fee.", i: <path d="M8 7l-5 5 5 5M16 7l5 5-5 5" /> },
  { t: "A brand mini-kit", d: "Logo files, colour palette and type choices you can reuse anywhere.", i: <><circle cx="8" cy="9" r="4" /><circle cx="16" cy="9" r="4" /><circle cx="12" cy="16" r="4" /></> },
  { t: "The research file", d: "What your reviews and competitors say, with a link to every source.", i: <><path d="M5 4h10l4 4v12H5z" /><path d="M9 12h6M9 16h6" /></> },
];

export default function Home() {
  return (
    <>
      <Header />
      <main className="overflow-x-clip">
        {/* hero: copy on the left, the live studio on the right */}
        <section className="wrap pt-12 md:pt-16">
          <div className="grid items-center gap-6 lg:grid-cols-[0.82fr_1.18fr] lg:gap-4">
            <div>
              <Reveal><div className="mono">AI web agency for small businesses</div></Reveal>
              <h1 className="mt-6 text-[clamp(40px,4.3vw,66px)] !leading-[1.08]">
                A website for your{" "}
                <RotatingText
                  texts={["café", "clinic", "salon", "bakery", "studio", "shop"]}
                  mainClassName="mr-[0.22em] inline-flex overflow-hidden align-bottom italic font-normal text-[var(--accent)]"
                  splitLevelClassName="overflow-hidden pb-[0.08em]"
                  staggerDuration={0.025}
                  staggerFrom="last"
                  rotationInterval={2400}
                  transition={{ type: "spring", damping: 30, stiffness: 400 }}
                />
                built by AI agents in 72 hours.
              </h1>
              <Reveal delay={0.15}>
                <p className="mt-7 max-w-[540px] text-[clamp(16px,1.3vw,19px)] text-[var(--muted)]">
                  Tell us about your business in a 15 minute chat. Six agents read your reviews and competitors, then design, write,
                  build and test the site while you watch. You approve it before it goes live, and the code is yours.
                </p>
              </Reveal>
              <Reveal delay={0.25}>
                <div className="mt-9 flex flex-wrap gap-3">
                  <a className="btn btn-primary" href="/app/new">Start a project <Arrow /></a>
                  <a className="btn btn-ghost" href="#floor">See how a project runs</a>
                </div>
              </Reveal>
            </div>
            <Reveal delay={0.1}>
              <div className="relative">
              <div className="relative aspect-square lg:aspect-auto lg:h-[clamp(540px,80vh,860px)]">
                <Diorama />
              </div>
                <div className="pointer-events-none mt-2 flex justify-between gap-4">
                  <span className="mono">The studio floor · live demo</span>
                  <span className="mono hidden sm:inline">Move your pointer to look around</span>
                </div>
              </div>
            </Reveal>
          </div>
          <div className="mt-14 grid grid-cols-2 border-y border-[var(--line)] md:grid-cols-4">
            {[["Fixed price", "₹24,999"], ["Delivery", "72 hours"], ["Revisions", "2 rounds"], ["Ownership", "Your code"]].map(([k, v], i) => (
              <Reveal key={k} delay={i * 0.06} className="border-[var(--line)] px-5 py-7 max-md:[&:nth-child(-n+2)]:border-b max-md:[&:nth-child(odd)]:border-r md:[&:not(:last-child)]:border-r">
                <span className="mono">{k}</span>
                <b className="serif mt-2 block text-[28px] font-semibold">{v}</b>
              </Reveal>
            ))}
          </div>
        </section>

        {/* moving band of the pipeline */}
        <div className="mt-24 overflow-hidden border-y border-[var(--line)] py-8 text-[var(--ink)]">
          <ScrollVelocity
            texts={["Research · Strategy · Art direction · Copy · Code · Testing · ", "Your reviews · Your voice · Your photos · Your code · "]}
            velocity={36}
            className="serif px-4 !text-[clamp(30px,5vw,64px)] font-semibold [&:nth-child(even)]:italic"
          />
        </div>

        {/* team */}
        <section id="team" className="wrap py-28">
          <SectionHead title="Six specialists. One brief. Every step on the record."
            text="Each agent has one job and limited permissions. A human creative director approves the visual direction before anything is built." />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {TEAM.map((m, i) => (
              <Reveal key={m.role} delay={(i % 3) * 0.08}>
                <article className="card flex h-full min-h-[240px] flex-col gap-3.5 p-6 transition-transform duration-300 hover:-translate-y-1">
                  <div className="flex items-center justify-between">
                    <div className="grid h-11 w-11 place-items-center rounded-lg" style={{ background: `color-mix(in srgb, ${m.color} 35%, var(--card))` }}>
                      <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="var(--ink)" strokeWidth="1.6" dangerouslySetInnerHTML={{ __html: m.icon }} />
                    </div>
                    <span className="mono">0{i + 1}</span>
                  </div>
                  <h3 className="text-[25px]">{m.role}</h3>
                  <p className="text-[15px] text-[var(--muted)]">{m.job}</p>
                  <div className="mt-auto border-t border-dashed border-[var(--line)] pt-3 text-[13px]"><b>Hands over:</b> {m.handsOver}</div>
                </article>
              </Reveal>
            ))}
          </div>
        </section>

        {/* statement */}
        <section className="wrap pb-28 pt-4">
          <SplitText text="Nothing happens behind a curtain." tag="h2" splitType="words" delay={60} duration={0.8} mask={false}
            className="max-w-[1100px] text-[clamp(40px,7vw,104px)] !leading-[1.08]" textAlign="left" />
        </section>

        {/* how a project runs */}
        <section id="floor" className="bg-[var(--bg2)] py-28">
          <div className="wrap">
            <SectionHead title="Watch your project move through the studio."
              text="Your project page shows each task as it happens, with every draft saved. Below is an example project, not a real client." />
            <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
              <Reveal>
                <div className="card overflow-hidden">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--line)] px-5 py-4">
                    <b>Kaapi House, a café in Pune</b><span className="chip">EXAMPLE PROJECT</span>
                  </div>
                  <ul className="m-0 list-none p-0">
                    {FLOOR.map((f, i) => (
                      <li key={i} className="grid grid-cols-[22px_1fr_auto] gap-3 border-b border-[var(--line)] px-5 py-4 text-[14.5px] last:border-b-0">
                        <i className={`dot ${f.s === "done" ? "dot-done" : f.s === "live" ? "dot-live" : ""}`} />
                        <div><div className="font-semibold">{f.who}</div><div className="text-[var(--muted)]">{f.what}</div></div>
                        <time className="mono !normal-case whitespace-nowrap">{f.at}</time>
                      </li>
                    ))}
                  </ul>
                </div>
              </Reveal>
              <Reveal delay={0.1}>
                <div className="card overflow-hidden">
                  <div className="flex items-center justify-between border-b border-[var(--line)] px-5 py-4"><b>Approved direction</b><span className="chip">STYLE TILE</span></div>
                  <div className="flex flex-col gap-3.5 p-5">
                    <div className="overflow-hidden rounded-lg border border-[var(--line)] bg-[#f7efe3]">
                      <div className="flex h-[130px] items-end bg-[#3b2a1e] p-4 serif text-2xl text-[#f7efe3]">Kaapi House</div>
                      <div className="grid grid-cols-3 gap-2 p-3">{[0, 1, 2].map((k) => <span key={k} className="h-12 rounded bg-[#e6d6c1]" />)}</div>
                    </div>
                    <div className="flex gap-1.5">{["#3b2a1e", "#f7efe3", "#b08d57", "#6e7f62"].map((c) => <i key={c} className="h-7 w-7 rounded-[5px] border border-black/10" style={{ background: c }} />)}</div>
                    <div className="mono">Headings: Fraunces · Body: Inter Tight</div>
                    <p className="text-[14.5px] text-[var(--muted)]">Comments you leave on the preview become tasks for the right agent. Two revision rounds are included.</p>
                  </div>
                </div>
              </Reveal>
            </div>
          </div>
        </section>

        {/* deliverables */}
        <section className="wrap py-28">
          <SectionHead title="What you get at handover." text="Everything is yours to keep, even if you never use Studio again." />
          <div className="card grid overflow-hidden sm:grid-cols-2 lg:grid-cols-4">
            {GETS.map((g, i) => (
              <Reveal key={g.t} delay={i * 0.07} className="border-[var(--line)] p-6 max-lg:border-b lg:[&:not(:last-child)]:border-r">
                <svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="var(--accent)" strokeWidth="1.6" aria-hidden>{g.i}</svg>
                <h3 className="mb-2 mt-3 text-xl">{g.t}</h3>
                <p className="text-[14.5px] text-[var(--muted)]">{g.d}</p>
              </Reveal>
            ))}
          </div>
        </section>

        {/* pricing */}
        <section id="pricing" className="bg-[var(--bg2)] py-28">
          <div className="wrap">
            <SectionHead title="One price, agreed before we start." text="Prices include GST. Anything outside the package is quoted in writing first." />
            <div className="grid gap-4 lg:grid-cols-3">
              {PLANS.map((p, i) => (
                <Reveal key={p.name} delay={i * 0.08}>
                  <div className={`card flex h-full flex-col gap-4 p-7 ${p.featured ? "!border-[1.5px] !border-[var(--ink)] shadow-[5px_5px_0_var(--accent)]" : ""}`}>
                    <div className="mono">{p.name}</div>
                    <div className="serif text-[42px] font-semibold leading-none">{p.price}<small className="font-sans text-[15px] font-normal text-[var(--muted)]">{p.unit}</small></div>
                    <p className="text-[var(--muted)]">{p.note}</p>
                    <ul className="m-0 flex list-none flex-col gap-2.5 p-0 text-[15px]">
                      {p.items.map((t) => <li key={t} className="flex gap-2.5"><Tick />{t}</li>)}
                    </ul>
                    <a href="#start" className={`btn mt-auto justify-center ${p.featured ? "btn-primary" : "btn-ghost"}`}>Choose {p.name}</a>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* faq */}
        <section id="faq" className="wrap grid gap-10 py-28 lg:grid-cols-[1fr_1.5fr]">
          <SplitText text="Questions owners ask us." tag="h2" splitType="words" mask={false} className="text-[clamp(32px,4vw,54px)] !leading-[1.12]" textAlign="left" />
          <div>
            {FAQ.map(([q, a], i) => (
              <Reveal key={q} delay={i * 0.05}>
                <details className="border-b border-[var(--line)] py-5" open={i === 0}>
                  <summary className="flex justify-between gap-4 serif text-[19px] font-semibold">
                    {q}<span className="plus font-sans text-2xl font-light text-[var(--muted)]">+</span>
                  </summary>
                  <p className="mt-2.5 max-w-[620px] text-[var(--muted)]">{a}</p>
                </details>
              </Reveal>
            ))}
          </div>
        </section>

        {/* cta */}
        <section id="start" className="wrap pb-10">
          <Reveal>
            <div className="grid items-end gap-8 rounded-[18px] bg-[var(--ink)] p-[clamp(32px,6vw,72px)] text-[var(--bg)] md:grid-cols-[1.4fr_1fr]">
              <div>
                <h2 className="text-[clamp(32px,4.4vw,58px)]">Tell us about your business. We will show you a direction by tomorrow.</h2>
                <p className="mt-4 text-[color-mix(in_srgb,var(--bg)_70%,transparent)]">The first chat is free and takes about 15 minutes. You pay only after you approve the direction.</p>
              </div>
              <a className="btn justify-self-start border-[var(--bg)] bg-[var(--bg)] text-[var(--ink)] hover:shadow-[3px_3px_0_var(--accent)]" href="/app/new">Start the brief chat <Arrow /></a>
            </div>
          </Reveal>
        </section>
      </main>
      <Footer />
    </>
  );
}
