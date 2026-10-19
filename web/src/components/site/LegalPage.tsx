import { Header, Footer } from "./Chrome";

export type LegalSection = { h: string; p: string[] };

export default function LegalPage({ title, updated, intro, sections }: {
  title: string; updated: string; intro: string; sections: LegalSection[];
}) {
  return (
    <>
      <Header />
      <main className="wrap max-w-[780px] py-20">
        <div className="mono">Last updated {updated}</div>
        <h1 className="mt-4 text-[clamp(38px,5vw,64px)]">{title}</h1>
        <p className="mt-6 text-lg text-[var(--muted)]">{intro}</p>
        {sections.map((s, i) => (
          <section key={s.h} className="mt-12">
            <h2 className="text-[26px]">{i + 1}. {s.h}</h2>
            {s.p.map((t, k) => <p key={k} className="mt-3 text-[var(--muted)]">{t}</p>)}
          </section>
        ))}
      </main>
      <Footer />
    </>
  );
}
