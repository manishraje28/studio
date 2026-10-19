"use client";

import { useEffect, useState } from "react";
import { api, type Details } from "@/lib/api";

/** The [placeholders] the copywriter left, as a form the owner fills in. Saving re-renders the preview. */
export default function DetailsPanel({ projectId, onSaved }: { projectId: string; onSaved: () => void }) {
  const [data, setData] = useState<Details | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    api.details(projectId).then((d) => {
      setData(d);
      setValues(Object.fromEntries(d.details.map((x) => [x.label, x.value])));
    }).catch(() => {});
  }, [projectId]);

  if (!data || data.details.length === 0) return null;
  const filled = Object.values(values).filter((v) => v.trim()).length;

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setNote(null);
    try {
      const d = await api.saveDetails(projectId, values);
      setData(d);
      setNote("Saved. The preview now shows your details.");
      onSaved();
    } catch (err) {
      setNote(err instanceof Error ? err.message : "Could not save");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={save} className="card p-5 sm:p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-[24px]">Your details</h2>
        <span className="mono">{filled} of {data.details.length} filled</span>
      </div>
      <p className="mt-1.5 text-[15px] text-[var(--muted)]">
        The team left these blank rather than guess. Fill in what you know; anything left empty stays highlighted in the preview.
      </p>
      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        {data.details.map((d) => (
          <label key={d.label} className="flex flex-col gap-1.5 text-sm font-semibold first-letter:uppercase">
            {d.label}
            <input
              className="field font-normal"
              maxLength={300}
              value={values[d.label] ?? ""}
              onChange={(e) => setValues((v) => ({ ...v, [d.label]: e.target.value }))}
            />
          </label>
        ))}
      </div>
      {data.questions.length > 0 && (
        <details className="mt-5 text-[14.5px]">
          <summary className="cursor-pointer font-semibold">Questions from the researcher ({data.questions.length})</summary>
          <ul className="mt-2 list-disc pl-5 text-[var(--muted)]">{data.questions.map((q) => <li key={q}>{q}</li>)}</ul>
        </details>
      )}
      <div className="mt-5 flex flex-wrap items-center gap-3">
        <button className="btn btn-primary" disabled={busy}>{busy ? "Saving" : "Save details"}</button>
        {note && <span className="text-sm text-[var(--muted)]">{note}</span>}
      </div>
    </form>
  );
}
