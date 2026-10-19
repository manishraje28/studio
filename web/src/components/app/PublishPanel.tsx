"use client";

import { useState } from "react";
import { API_URL, api, auth, type Project } from "@/lib/api";

/** Handover: put the site live on its own link, and download the files to keep. */
export default function PublishPanel({ project, liveUrl, onPublishing }: {
  project: Project;
  liveUrl: string | null;
  onPublishing: (p: Project) => void;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const publishing = project.status === "preview" && busy === "publishing";

  async function publish() {
    setBusy("publishing");
    setError(null);
    try {
      onPublishing(await api.publish(project.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not publish");
      setBusy(null);
    }
  }

  async function download() {
    setBusy("download");
    setError(null);
    try {
      const res = await fetch(`${API_URL}/projects/${project.id}/export`, {
        headers: { Authorization: `Bearer ${auth.get() ?? ""}` },
      });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail ?? "Download failed");
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = /filename="([^"]+)"/.exec(res.headers.get("content-disposition") ?? "")?.[1] ?? "website.zip";
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Download failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="rounded-[10px] border-[1.5px] border-[var(--ink)] bg-[var(--card)] p-5 shadow-[4px_4px_0_var(--accent)] sm:p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-[24px]">{liveUrl ? "Your site is live" : "Ready to go live?"}</h2>
        {liveUrl && <span className="chip">LIVE</span>}
      </div>
      {liveUrl ? (
        <p className="mt-2 text-[15px]">
          <a href={liveUrl} target="_blank" rel="noopener noreferrer" className="serif break-all text-[22px] font-semibold text-[var(--accent)]">
            {liveUrl.replace("https://", "")}
          </a>
          <span className="mt-1 block text-[var(--muted)]">Share this link anywhere. Publishing again updates the same address.</span>
        </p>
      ) : (
        <p className="mt-1.5 text-[15px] text-[var(--muted)]">
          Publishing puts this version on its own address with HTTPS, free. You can keep changing details and photos and publish again.
        </p>
      )}
      <div className="mt-5 flex flex-wrap items-center gap-3">
        <button className="btn btn-primary" onClick={publish} disabled={!!busy}>
          {publishing ? "Publishing" : liveUrl ? "Publish changes" : "Approve and publish"}
        </button>
        <button className="btn btn-ghost" onClick={download} disabled={!!busy}>
          {busy === "download" ? "Preparing download" : "Download site (.zip)"}
        </button>
      </div>
      {error && <p className="mt-3 text-sm text-[#b42318]">{error}</p>}
    </div>
  );
}
