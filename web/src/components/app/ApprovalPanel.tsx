"use client";

import { useState } from "react";
import { api, type Project } from "@/lib/api";

/** Shown while the visual direction waits for the owner: approve it or send notes back. */
export default function ApprovalPanel({ projectId, onDone }: { projectId: string; onDone: (p: Project) => void }) {
  const [mode, setMode] = useState<"choose" | "revise">("choose");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send(decision: "approve" | "revise") {
    setBusy(true);
    setError(null);
    try {
      onDone(await api.decideDirection(projectId, decision, decision === "revise" ? note : undefined));
      setMode("choose");
      setNote("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-[10px] border-[1.5px] border-[var(--ink)] bg-[var(--card)] p-5 shadow-[4px_4px_0_var(--accent)]">
      <h2 className="text-[24px]">Approve the visual direction</h2>
      <p className="mt-1.5 text-[15px] text-[var(--muted)]">
        Nothing gets written or built until you are happy with how the site will look. You can ask for changes as often as you need.
      </p>
      {mode === "choose" ? (
        <div className="mt-4 flex flex-wrap gap-3">
          <button className="btn btn-primary" disabled={busy} onClick={() => send("approve")}>
            {busy ? "Sending" : "Approve and start the copy"}
          </button>
          <button className="btn btn-ghost" disabled={busy} onClick={() => setMode("revise")}>Ask for changes</button>
        </div>
      ) : (
        <form className="mt-4 flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); send("revise"); }}>
          <label className="flex flex-col gap-1.5 text-sm font-semibold">
            What should the art director change?
            <textarea className="field font-normal" required minLength={5} maxLength={1000} value={note}
              placeholder="For example: warmer colours, a less formal heading font, more green from the plants"
              onChange={(e) => setNote(e.target.value)} />
          </label>
          <div className="flex flex-wrap gap-3">
            <button className="btn btn-primary" disabled={busy || note.trim().length < 5}>{busy ? "Sending" : "Send notes"}</button>
            <button type="button" className="btn btn-ghost" onClick={() => setMode("choose")}>Cancel</button>
          </div>
        </form>
      )}
      {error && <p className="mt-3 text-sm text-[#b42318]">{error}</p>}
    </div>
  );
}
