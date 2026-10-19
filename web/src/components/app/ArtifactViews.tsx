"use client";

import { useEffect, useState } from "react";

type Fact = { claim: string; source: "brief" | "website" | "general knowledge" };
type Research = {
  summary: string;
  audiences: string[];
  what_customers_value: string[];
  differentiators: string[];
  tone_words: string[];
  facts: Fact[];
  open_questions: string[];
};
type Strategy = {
  positioning: string;
  primary_audience: string;
  primary_action: { label: string; why: string };
  messaging_pillars: string[];
  pages: { slug: string; title: string; goal: string; sections: string[] }[];
  seo_keywords: string[];
};

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-t border-[var(--line)] pt-5 first:border-t-0 first:pt-0">
      <h3 className="mb-2.5 text-lg">{title}</h3>
      {children}
    </div>
  );
}

const List = ({ items }: { items: string[] }) => (
  <ul className="m-0 flex list-disc flex-col gap-1 pl-5 text-[15px]">{items.map((t) => <li key={t}>{t}</li>)}</ul>
);

const SOURCE_STYLE: Record<Fact["source"], string> = {
  brief: "border-[var(--ink)] text-[var(--ink)]",
  website: "border-[var(--accent)] text-[var(--accent)]",
  "general knowledge": "border-[var(--line)] text-[var(--muted)]",
};

export function ResearchView({ content }: { content: Record<string, unknown> }) {
  const r = content as Research;
  return (
    <div className="flex flex-col gap-6">
      <Block title="Summary"><p className="text-[15.5px]">{r.summary}</p></Block>
      <div className="grid gap-6 sm:grid-cols-2">
        <Block title="Who it is for"><List items={r.audiences} /></Block>
        <Block title="What they value"><List items={r.what_customers_value} /></Block>
      </div>
      {r.differentiators.length > 0 && <Block title="What sets it apart"><List items={r.differentiators} /></Block>}
      <Block title="Voice">
        <div className="flex flex-wrap gap-2">{r.tone_words.map((w) => <span key={w} className="chip !text-[12px] !normal-case">{w}</span>)}</div>
      </Block>
      <Block title="Facts and where they come from">
        <ul className="m-0 flex list-none flex-col gap-2 p-0">
          {r.facts.map((f) => (
            <li key={f.claim} className="flex flex-wrap items-start justify-between gap-2 text-[15px]">
              <span className="min-w-0 flex-1">{f.claim}</span>
              <span className={`shrink-0 rounded-[4px] border px-1.5 py-0.5 font-mono text-[11px] ${SOURCE_STYLE[f.source]}`}>{f.source}</span>
            </li>
          ))}
        </ul>
      </Block>
      {r.open_questions.length > 0 && (
        <Block title="Questions for you">
          <List items={r.open_questions} />
          <p className="mt-3 text-sm text-[var(--muted)]">The more of these you can answer, the more accurate the copy will be.</p>
        </Block>
      )}
    </div>
  );
}

export function StrategyView({ content }: { content: Record<string, unknown> }) {
  const s = content as Strategy;
  return (
    <div className="flex flex-col gap-6">
      <Block title="Positioning"><p className="serif text-[21px] !leading-[1.35]">{s.positioning}</p></Block>
      <div className="grid gap-6 sm:grid-cols-2">
        <Block title="Main action">
          <span className="btn btn-primary pointer-events-none !py-2 !text-sm">{s.primary_action.label}</span>
          <p className="mt-2 text-sm text-[var(--muted)]">{s.primary_action.why}</p>
        </Block>
        <Block title="Primary audience"><p className="text-[15px]">{s.primary_audience}</p></Block>
      </div>
      <Block title="Messaging pillars"><List items={s.messaging_pillars} /></Block>
      <Block title="Sitemap">
        <ol className="m-0 grid list-none gap-3 p-0 sm:grid-cols-2">
          {s.pages.map((p) => (
            <li key={p.slug || "home"} className="rounded-lg border border-[var(--line)] bg-[var(--bg)] p-4">
              <div className="flex items-baseline justify-between gap-2">
                <b className="serif text-[18px]">{p.title}</b>
                <code className="font-mono text-[12px] text-[var(--muted)]">/{p.slug}</code>
              </div>
              <p className="mt-1 text-sm text-[var(--muted)]">{p.goal}</p>
              <ul className="mt-2 flex list-none flex-wrap gap-1.5 p-0">
                {p.sections.map((sec) => <li key={sec} className="rounded-[4px] bg-[var(--bg2)] px-2 py-0.5 text-[12.5px]">{sec}</li>)}
              </ul>
            </li>
          ))}
        </ol>
      </Block>
      <Block title="Search terms">
        <div className="flex flex-wrap gap-2">{s.seo_keywords.map((k) => <span key={k} className="chip !text-[12px] !normal-case">{k}</span>)}</div>
      </Block>
    </div>
  );
}

type Style = {
  mood: string;
  palette: Record<"background" | "surface" | "ink" | "muted" | "accent" | "accent_ink", string>;
  typography: { heading_font: string; body_font: string; heading_style: string; why: string };
  signature_ideas: { name: string; description: string; why_it_fits: string }[];
  imagery: string;
  layout_notes: string[];
  avoid: string[];
};

/** Loads the chosen Google Fonts once so the style tile shows real type, not a fallback. */
function useGoogleFonts(families: string[]) {
  const key = families.join("|");
  useEffect(() => {
    const href = `https://fonts.googleapis.com/css2?${key
      .split("|")
      .map((f) => `family=${encodeURIComponent(f).replace(/%20/g, "+")}:ital,wght@0,400;0,600;1,400`)
      .join("&")}&display=swap`;
    if (document.querySelector(`link[href="${href}"]`)) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    document.head.appendChild(link);
  }, [key]);
}

export function StyleView({ content, businessName, actionLabel }: { content: Record<string, unknown>; businessName: string; actionLabel?: string }) {
  const s = content as Style;
  const p = s.palette;
  useGoogleFonts([s.typography.heading_font, s.typography.body_font]);
  const heading = { fontFamily: `"${s.typography.heading_font}", Georgia, serif` };
  const body = { fontFamily: `"${s.typography.body_font}", system-ui, sans-serif` };

  return (
    <div className="flex flex-col gap-6">
      {/* a small page in the proposed style */}
      <div className="overflow-hidden rounded-lg border border-[var(--line)]" style={{ background: p.background, color: p.ink, ...body }}>
        <div className="flex items-center justify-between px-5 py-3 text-[13px]" style={{ borderBottom: `1px solid ${p.surface}` }}>
          <b style={heading}>{businessName}</b>
          <span style={{ color: p.muted }}>Menu · Visit · About</span>
        </div>
        <div className="px-5 py-8">
          <div className="text-[clamp(26px,3.4vw,38px)] leading-[1.08]" style={{ ...heading, fontStyle: s.typography.heading_style === "italic accents" ? "italic" : undefined }}>
            {businessName}
          </div>
          <p className="mt-3 max-w-[420px] text-[14.5px]" style={{ color: p.muted }}>{s.mood}</p>
          <span className="mt-5 inline-block rounded-[5px] px-4 py-2 text-[14px] font-semibold" style={{ background: p.accent, color: p.accent_ink }}>
            {actionLabel ?? "Get in touch"}
          </span>
          <div className="mt-6 grid grid-cols-3 gap-2">
            {[0, 1, 2].map((i) => <div key={i} className="h-14 rounded" style={{ background: p.surface }} />)}
          </div>
        </div>
      </div>

      <Block title="Palette">
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
          {Object.entries(p).map(([role, hex]) => (
            <div key={role}>
              <div className="h-12 rounded-md border border-black/10" style={{ background: hex }} />
              <div className="mt-1 text-[12px] font-semibold">{role.replace("_", " ")}</div>
              <code className="font-mono text-[11px] text-[var(--muted)]">{hex}</code>
            </div>
          ))}
        </div>
        <p className="mt-2 text-sm text-[var(--muted)]">Every text colour passes WCAG contrast checks against its background.</p>
      </Block>
      <Block title="Type">
        <div className="text-[28px] leading-tight" style={heading}>{s.typography.heading_font}</div>
        <div className="mt-1 text-[16px]" style={body}>{s.typography.body_font} for body text. {s.typography.why}</div>
      </Block>
      <Block title="Signature idea">
        {s.signature_ideas.map((i) => (
          <div key={i.name} className="mb-3 last:mb-0">
            <b>{i.name}</b>
            <p className="text-[15px]">{i.description}</p>
            <p className="text-sm text-[var(--muted)]">From the research: {i.why_it_fits}</p>
          </div>
        ))}
      </Block>
      <div className="grid gap-6 sm:grid-cols-2">
        <Block title="Layout"><List items={s.layout_notes} /></Block>
        <Block title="This design avoids"><List items={s.avoid} /></Block>
      </div>
      <Block title="Photos"><p className="text-[15px]">{s.imagery}</p></Block>
    </div>
  );
}

type Copy = { pages: { slug: string; seo_title: string; meta_description: string; sections: { section: string; heading: string; body: string; cta_label: string | null }[] }[] };

/** Square-bracket placeholders are details the owner still has to give us; make them stand out. */
function Placeholders({ text }: { text: string }) {
  return (
    <>
      {text.split(/(\[[^\]]+\])/g).map((part, i) =>
        part.startsWith("[") ? (
          <mark key={i} className="rounded-[3px] bg-[color-mix(in_srgb,var(--r3)_45%,transparent)] px-1 text-[var(--ink)]">{part}</mark>
        ) : (
          part
        ),
      )}
    </>
  );
}

type EditFn = (slug: string, index: number, body: { heading: string; body: string; cta_label: string | null }) => Promise<void>;

function SectionCard({ s, onSave }: { s: Copy["pages"][number]["sections"][number]; onSave?: (b: { heading: string; body: string; cta_label: string | null }) => Promise<void> }) {
  const [editing, setEditing] = useState(false);
  const [heading, setHeading] = useState(s.heading);
  const [body, setBody] = useState(s.body);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (editing && onSave) {
    return (
      <form
        className="flex flex-col gap-2 rounded-lg border-[1.5px] border-[var(--ink)] bg-[var(--card)] p-4"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError(null);
          try {
            await onSave({ heading, body, cta_label: s.cta_label });
            setEditing(false);
          } catch (err) {
            setError(err instanceof Error ? err.message : "Could not save");
          } finally {
            setBusy(false);
          }
        }}
      >
        <div className="mono !text-[10.5px]">{s.section}</div>
        <input className="field serif !text-[18px]" value={heading} maxLength={90} onChange={(e) => setHeading(e.target.value)} />
        <textarea className="field" value={body} maxLength={900} onChange={(e) => setBody(e.target.value)} />
        {error && <p className="text-sm text-[#b42318]">{error}</p>}
        <div className="flex gap-2">
          <button className="btn btn-primary !py-1.5 !text-[13px]" disabled={busy}>{busy ? "Saving" : "Save"}</button>
          <button type="button" className="btn btn-ghost !py-1.5 !text-[13px]" onClick={() => { setEditing(false); setHeading(s.heading); setBody(s.body); }}>Cancel</button>
        </div>
      </form>
    );
  }
  return (
    <section className="group relative rounded-lg border border-[var(--line)] bg-[var(--bg)] p-4">
      <div className="mono !text-[10.5px]">{s.section}</div>
      <h4 className="serif mt-1 text-[20px] font-semibold leading-snug"><Placeholders text={s.heading} /></h4>
      {s.body && <p className="mt-1.5 whitespace-pre-line text-[15px]"><Placeholders text={s.body} /></p>}
      {s.cta_label && <span className="btn btn-primary pointer-events-none mt-3 !py-1.5 !text-[13px]">{s.cta_label}</span>}
      {onSave && (
        <button className="absolute right-3 top-3 cursor-pointer rounded-[5px] border border-[var(--line)] bg-[var(--card)] px-2.5 py-1 text-[12px] font-semibold hover:border-[var(--ink)]" onClick={() => setEditing(true)}>
          Edit
        </button>
      )}
    </section>
  );
}

export function CopyView({ content, onEdit }: { content: Record<string, unknown>; onEdit?: EditFn }) {
  const c = content as Copy;
  return (
    <div className="flex flex-col gap-8">
      <p className="text-sm text-[var(--muted)]">
        Highlighted text in [brackets] is a detail we need from you. Nothing was made up to fill it.
        {onEdit && " Use Edit on any section to fix the wording yourself."}
      </p>
      {c.pages.map((page) => (
        <article key={page.slug || "home"} className="border-t border-[var(--line)] pt-6 first:border-t-0 first:pt-0">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h3 className="text-2xl">{page.seo_title}</h3>
            <code className="font-mono text-[12px] text-[var(--muted)]">/{page.slug}</code>
          </div>
          <p className="mt-1 text-sm text-[var(--muted)]">Search description: {page.meta_description}</p>
          <div className="mt-4 flex flex-col gap-4">
            {page.sections.map((s, i) => (
              <SectionCard key={`${page.slug}-${i}-${s.heading}`} s={s} onSave={onEdit ? (b) => onEdit(page.slug, i, b) : undefined} />
            ))}
          </div>
        </article>
      ))}
    </div>
  );
}

type QA = {
  score: number;
  findings: { page: string; check: string; severity: "pass" | "warn" | "fail"; message: string }[];
  review: { specificity: number; summary: string; generic_lines: { page: string; text: string; why: string; suggestion: string }[] };
};

const SEV: Record<string, string> = { fail: "#b42318", warn: "#b54708", pass: "#2f6f4f" };

export function QAView({ content }: { content: Record<string, unknown> }) {
  const q = content as QA;
  const issues = q.findings.filter((f) => f.severity !== "pass");
  const passed = q.findings.length - issues.length;
  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-lg border border-[var(--line)] bg-[var(--bg)] p-4">
          <div className="mono">Site checks</div>
          <div className="serif mt-1 text-[36px] font-semibold">{q.score}<small className="text-base text-[var(--muted)]">/100</small></div>
          <div className="text-sm text-[var(--muted)]">{passed} checks passed</div>
        </div>
        <div className="rounded-lg border border-[var(--line)] bg-[var(--bg)] p-4">
          <div className="mono">Copy specificity</div>
          <div className="serif mt-1 text-[36px] font-semibold">{q.review.specificity}<small className="text-base text-[var(--muted)]">/10</small></div>
          <div className="text-sm text-[var(--muted)]">How clearly it could only be you</div>
        </div>
      </div>
      <Block title="What to look at">
        {issues.length === 0 ? (
          <p className="text-[15px]">Nothing to fix. Every page passed.</p>
        ) : (
          <ul className="m-0 flex list-none flex-col gap-2 p-0">
            {issues.map((f, i) => (
              <li key={i} className="flex flex-wrap items-baseline gap-2 text-[15px]">
                <span className="rounded-[4px] border px-1.5 font-mono text-[11px] uppercase" style={{ color: SEV[f.severity], borderColor: SEV[f.severity] }}>{f.severity}</span>
                <b>/{f.page === "home" ? "" : f.page}</b>
                <span>{f.check}: {f.message}</span>
              </li>
            ))}
          </ul>
        )}
      </Block>
      <Block title="Editor's notes">
        <p className="text-[15px]">{q.review.summary}</p>
        <ul className="mt-3 flex list-none flex-col gap-3 p-0">
          {q.review.generic_lines.map((g, i) => (
            <li key={i} className="rounded-lg border border-[var(--line)] bg-[var(--bg)] p-3.5 text-[14.5px]">
              <div className="text-[var(--muted)] line-through decoration-[var(--muted)]/50">{g.text}</div>
              <div className="mt-1 font-semibold">{g.suggestion}</div>
              <div className="mt-1 text-[13px] text-[var(--muted)]">{g.why} · /{g.page === "home" ? "" : g.page}</div>
            </li>
          ))}
        </ul>
      </Block>
    </div>
  );
}
