"use client";

import { useEffect, useState } from "react";
import { api, type Project, type Revision } from "@/lib/api";

const EXAMPLES = [
  "Mention bridal makeup in the main heading",
  "Add a Diwali offers section to the services page",
  "Make the colours greener and calmer",
  "Remove the FAQ",
];

/** Change requests in plain words, plus the history with undo. The live site changes only on publish. */
export default function RevisionPanel({ project, onChange }: { project: Project; onChange: (p: Project) => void }) {
  const [request, setRequest] = useState("");
  const [history, setHistory] = useState<Revision[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const working = project.status === "revising";

  useEffect(() => {
    api.revisions(project.id).then(setHistory).catch(() => {});
  }, [project.id, project.status, project.updated_at]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onChange(await api.requestRevision(project.id, request.trim()));
      setRequest("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send");
    } finally {
      setBusy(false);
    }
  }

  async function undo(version: number) {
    setBusy(true);
    setError(null);
    try {
      onChange(await api.undoRevision(project.id, version));
      setHistory(await api.revisions(project.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not undo");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card p-5 sm:p-6">
      <h2 className="text-[24px]">Request changes</h2>
      <p className="mt-1.5 text-[15px] text-[var(--muted)]">
        Say what you want in your own words. The team changes only that, and your live site stays as it is until you publish again.
      </p>
      <form onSubmit={send} className="mt-4 flex flex-col gap-3">
        <textarea
          className="field"
          required
          minLength={4}
          maxLength={1500}
          value={request}
          disabled={working}
          placeholder={EXAMPLES[0]}
          onChange={(e) => setRequest(e.target.value)}
        />
        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <button key={ex} type="button" onClick={() => setRequest(ex)} disabled={working}
              className="cursor-pointer rounded-[5px] border border-[var(--line)] px-2.5 py-1 text-[13px] text-[var(--muted)] hover:border-[var(--ink)] hover:text-[var(--ink)]">
              {ex}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button className="btn btn-primary" disabled={busy || working || request.trim().length < 4}>
            {working ? "The team is working on it" : "Send to the team"}
          </button>
          {working && <span className="text-sm text-[var(--muted)]">Follow along on the studio floor below.</span>}
        </div>
      </form>
      {error && <p className="mt-3 text-sm text-[#b42318]">{error}</p>}

      {history.length > 0 && (
        <div className="mt-6 border-t border-[var(--line)] pt-5">
          <h3 className="text-lg">History</h3>
          <ul className="mt-3 flex list-none flex-col gap-3 p-0">
            {history.map((r) => (
              <li key={r.version} className="flex flex-wrap items-start justify-between gap-3 rounded-lg border border-[var(--line)] bg-[var(--bg)] p-3.5">
                <div className="min-w-0 flex-1">
                  <div className="font-semibold">{r.request}</div>
                  <div className="text-[14px] text-[var(--muted)]">{r.changes.join("; ") || r.summary}</div>
                  {r.out_of_scope && <div className="mt-1 text-[13px] text-[#b54708]">{r.out_of_scope}</div>}
                  <time className="mono !normal-case !text-[11px]">{new Date(r.created_at).toLocaleString()}</time>
                </div>
                {!r.request.startsWith("Undo:") && (
                  <button className="btn btn-ghost !px-3 !py-1.5 !text-[13px]" disabled={busy || working} onClick={() => undo(r.version)}>
                    Undo
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
