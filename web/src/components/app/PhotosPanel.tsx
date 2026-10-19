"use client";

import { useEffect, useRef, useState } from "react";
import { API_URL, api, type OwnerPhoto, type Project } from "@/lib/api";

const MAX = 12;

/** The owner's own photos. They always come before stock photos in the generated site. */
export default function PhotosPanel({ projectId, onChanged, onRebuild }: {
  projectId: string;
  onChanged: () => void;
  onRebuild: (p: Project) => void;
}) {
  const [photos, setPhotos] = useState<OwnerPhoto[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.photos(projectId).then(setPhotos).catch(() => {});
  }, [projectId]);

  async function upload(files: FileList | null) {
    if (!files?.length) return;
    setError(null);
    const list = [...files].slice(0, MAX - photos.length);
    for (const [i, f] of list.entries()) {
      setBusy(`Uploading ${i + 1} of ${list.length}`);
      try {
        setPhotos(await api.uploadPhoto(projectId, f));
        setDirty(true);
      } catch (e) {
        setError(`${f.name}: ${e instanceof Error ? e.message : "upload failed"}`);
      }
    }
    setBusy(null);
    if (input.current) input.current.value = "";
    onChanged();
  }

  async function remove(name: string) {
    setBusy("Removing");
    try {
      setPhotos(await api.deletePhoto(projectId, name));
      setDirty(true);
      onChanged();
    } finally {
      setBusy(null);
    }
  }

  async function rebuild() {
    setBusy("Asking the developer");
    try {
      onRebuild(await api.rebuild(projectId));
      setDirty(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not rebuild");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="card p-5 sm:p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-[24px]">Your photos</h2>
        <span className="mono">{photos.length} of {MAX}</span>
      </div>
      <p className="mt-1.5 text-[15px] text-[var(--muted)]">
        Real photos of your place, products and work make the site yours. They are used before any stock photos.
        We resize them and remove location data.
      </p>

      <div className="mt-5 grid grid-cols-3 gap-3 sm:grid-cols-6">
        {photos.map((p) => (
          <figure key={p.name} className="group relative m-0 aspect-square overflow-hidden rounded-lg border border-[var(--line)]">
            {/* eslint-disable-next-line @next/next/no-img-element -- served by the API with a signed token */}
            <img src={`${API_URL}${p.url}`} alt={p.alt} className="h-full w-full object-cover" />
            <button
              type="button"
              onClick={() => remove(p.name)}
              disabled={!!busy}
              className="absolute right-1.5 top-1.5 cursor-pointer rounded-[5px] bg-[var(--ink)] px-2 py-1 text-[12px] font-semibold text-[var(--bg)] opacity-90 hover:opacity-100"
              aria-label={`Remove ${p.alt}`}
            >
              Remove
            </button>
          </figure>
        ))}
        {photos.length < MAX && (
          <button
            type="button"
            onClick={() => input.current?.click()}
            disabled={!!busy}
            className="flex aspect-square cursor-pointer flex-col items-center justify-center gap-1 rounded-lg border-[1.5px] border-dashed border-[var(--line)] text-[13px] font-semibold text-[var(--muted)] hover:border-[var(--ink)] hover:text-[var(--ink)]"
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden><path d="M12 5v14M5 12h14" /></svg>
            Add photos
          </button>
        )}
      </div>
      <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" multiple hidden onChange={(e) => upload(e.target.files)} />

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <button className="btn btn-primary" onClick={rebuild} disabled={!!busy || !dirty}>
          Rebuild the site with these photos
        </button>
        {busy && <span className="text-sm text-[var(--muted)]">{busy}</span>}
        {!busy && !dirty && photos.length > 0 && <span className="text-sm text-[var(--muted)]">The preview already uses these.</span>}
      </div>
      {error && <p className="mt-3 text-sm text-[#b42318]">{error}</p>}
    </div>
  );
}
