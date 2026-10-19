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
