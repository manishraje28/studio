"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type Project } from "@/lib/api";
import { STATUS_LABEL } from "@/components/app/status";

export default function Projects() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.projects().then(setProjects).catch((e) => setError(e.message));
  }, []);

  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h1 className="text-[clamp(32px,4vw,48px)]">Your projects</h1>
        <Link href="/app/new" className="btn btn-primary">Start a project</Link>
      </div>
      {error && <p className="mt-6 text-[#b42318]">Could not load projects: {error}</p>}
      {projects?.length === 0 && (
        <div className="card mt-10 p-8">
          <h2 className="text-2xl">No projects yet</h2>
          <p className="mt-2 text-[var(--muted)]">Fill in the brief and the team starts right away. It takes about 5 minutes.</p>
        </div>
      )}
      <ul className="mt-10 grid list-none gap-3 p-0">
        {projects?.map((p) => (
          <li key={p.id}>
            <Link href={`/app/projects/${p.id}`} className="card flex flex-wrap items-center justify-between gap-3 p-5 no-underline transition-colors hover:border-[var(--ink)]">
              <div>
                <div className="serif text-[22px] font-semibold">{p.business_name}</div>
                <div className="text-sm text-[var(--muted)]">{p.business_type}{p.city ? `, ${p.city}` : ""}</div>
              </div>
              <span className="chip">{STATUS_LABEL[p.status]}</span>
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}
