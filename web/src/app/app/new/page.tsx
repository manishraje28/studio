"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";

const QUESTIONS = [
  { key: "what_we_do", label: "What do you sell or offer?", hint: "Be specific: dishes, services, what people come back for.", long: true },
  { key: "audience", label: "Who are your customers?", hint: "For example: college students, families on weekends, local offices.", long: true },
  { key: "main_goal", label: "What should the website get people to do?", hint: "Book a table, call you, visit the shop, request a quote.", long: false },
  { key: "tone", label: "How should it feel?", hint: "Three words, for example: warm, unhurried, honest.", long: false },
  { key: "avoid", label: "Anything to avoid?", hint: "Optional. Colours, words or styles you do not want.", long: false },
] as const;

export default function NewProject() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(form: FormData) {
    setBusy(true);
    setError(null);
    const answers: Record<string, string> = {};
    for (const q of QUESTIONS) {
      const v = String(form.get(q.key) ?? "").trim();
      if (v) answers[q.key] = v;
    }
    try {
      const website = String(form.get("website_url") ?? "").trim();
      const project = await api.createProject({
        business_name: String(form.get("business_name")).trim(),
        business_type: String(form.get("business_type")).trim(),
        city: String(form.get("city") ?? "").trim() || undefined,
        website_url: website ? (website.startsWith("http") ? website : `https://${website}`) : undefined,
        answers,
      });
      router.push(`/app/projects/${project.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-[720px]">
      <div className="mono">New project</div>
      <h1 className="mt-3 text-[clamp(34px,4.4vw,54px)] !leading-[1.1]">Tell the team about your business.</h1>
      <p className="mt-4 text-[var(--muted)]">
        The researcher reads this and your current website first, so specific answers make a better site.
        Nothing here is published without your approval.
      </p>

      <form action={submit} className="mt-10 flex flex-col gap-8">
        <fieldset className="grid gap-5 sm:grid-cols-2">
          <legend className="serif mb-4 text-2xl font-semibold">The basics</legend>
          <Field label="Business name" name="business_name" required minLength={2} placeholder="Kaapi House" />
          <Field label="Type of business" name="business_type" required minLength={2} placeholder="Café" />
          <Field label="City" name="city" placeholder="Pune" />
          <Field label="Current website (optional)" name="website_url" placeholder="kaapihouse.in" />
        </fieldset>

        <fieldset className="flex flex-col gap-5">
          <legend className="serif mb-4 text-2xl font-semibold">The brief</legend>
          {QUESTIONS.map((q) => (
            <label key={q.key} className="flex flex-col gap-1.5">
              <span className="font-semibold">{q.label}</span>
              <span className="text-sm text-[var(--muted)]">{q.hint}</span>
              {q.long ? (
                <textarea name={q.key} maxLength={2000} className="field mt-1" />
              ) : (
                <input name={q.key} maxLength={2000} className="field mt-1" />
              )}
            </label>
          ))}
        </fieldset>

        {error && <p className="text-[#b42318]">{error}</p>}
        <div className="flex flex-wrap items-center gap-4">
          <button className="btn btn-primary" disabled={busy}>{busy ? "Sending to the team" : "Start the project"}</button>
          <span className="text-sm text-[var(--muted)]">Free demo: 3 projects per day.</span>
        </div>
      </form>
    </div>
  );
}

function Field({ label, ...input }: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="flex flex-col gap-1.5 text-sm font-semibold">
      {label}
      <input className="field font-normal" maxLength={160} {...input} />
    </label>
  );
}
