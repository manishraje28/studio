"use client";

import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api, streamEvents, type AgentEvent, type Artifact, type Project } from "@/lib/api";
import { TEAM } from "@/lib/team";
import { STAGES, STATUS_LABEL, stageIndex } from "@/components/app/status";
import { CopyView, ResearchView, StrategyView, StyleView } from "@/components/app/ArtifactViews";
import ApprovalPanel from "@/components/app/ApprovalPanel";

const TAB_LABEL: Record<string, string> = { research: "Research file", strategy: "Strategy", style: "Style tile", copy: "Copy" };
const TAB_ORDER = ["research", "strategy", "style", "copy"];

const AGENT_COLOR: Record<string, string> = Object.fromEntries(TEAM.map((a) => [a.role, a.color]));

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<string | null>(null);
  const seen = useRef(new Set<number>());

  useEffect(() => {
    const refresh = () => {
      api.project(id).then(setProject).catch((e) => setError(e.message));
      api.artifacts(id).then(setArtifacts).catch(() => {});
    };
    refresh();
    const stop = streamEvents(id, (ev) => {
      if (seen.current.has(ev.id)) return;
      seen.current.add(ev.id);
      setEvents((prev) => [...prev, ev]);
      // New deliverable or status change: pull fresh project state.
      if (ev.kind === "artifact" || ev.kind === "status" || ev.kind === "error") refresh();
    });
    return stop;
  }, [id]);

  if (error) return <p className="text-[#b42318]">{error}</p>;
  if (!project) return <p className="mono">Loading</p>;

  const latest = new Map<string, Artifact>();
  for (const a of artifacts) if (!latest.has(a.kind) || latest.get(a.kind)!.version < a.version) latest.set(a.kind, a);
  const kinds = [...latest.keys()].sort((a, b) => TAB_ORDER.indexOf(a) - TAB_ORDER.indexOf(b));
  const active = tab && latest.has(tab) ? tab : kinds.at(-1) ?? null;
  const current = stageIndex(project.status);
  const working = !["failed", "awaiting_approval", "building"].includes(project.status);
  const style = latest.get("style");
  const strategy = latest.get("strategy")?.content as { primary_action?: { label: string } } | undefined;

  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="mono">{project.business_type}{project.city ? ` · ${project.city}` : ""}</div>
          <h1 className="mt-2 text-[clamp(34px,4.4vw,56px)]">{project.business_name}</h1>
        </div>
        <span className="chip !text-[12px]">{STATUS_LABEL[project.status]}</span>
      </div>

      {/* stage rail */}
      <ol className="mt-8 grid list-none grid-cols-4 gap-2 p-0 sm:grid-cols-7">
        {STAGES.map((s) => {
          const idx = stageIndex(s.status);
          const state = project.status === "failed" ? "todo" : idx < current ? "done" : idx === current ? "now" : "todo";
          return (
            <li key={s.status} className="flex flex-col gap-2">
              <span className={`h-1.5 rounded-full ${state === "done" ? "bg-[var(--accent)]" : state === "now" ? "bg-[var(--ink)]" : "bg-[var(--line)]"}`} />
              <span className={`text-[13px] ${state === "todo" ? "text-[var(--muted)]" : "font-semibold"}`}>{s.label}</span>
            </li>
          );
        })}
      </ol>

      {project.status === "awaiting_approval" && (
        <div className="mt-8">
          <ApprovalPanel projectId={project.id} onDone={(p) => { setProject(p); setTab(null); }} />
        </div>
      )}

      <div className="mt-10 grid gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.3fr)]">
        {/* live log */}
        <section className="card self-start overflow-hidden">
          <div className="flex items-center justify-between border-b border-[var(--line)] px-5 py-4">
            <b>Studio floor</b>
            <span className="mono flex items-center gap-2">
              {working && <i className="dot dot-live !mt-0 !h-2 !w-2" />}
              {working ? "Live" : "Idle"}
            </span>
          </div>
          <ul className="m-0 max-h-[560px] list-none overflow-y-auto p-0">
            {events.length === 0 && <li className="px-5 py-6 text-[var(--muted)]">Waiting for the first agent to pick this up.</li>}
            {events.map((e) => (
              <li key={e.id} className="grid grid-cols-[10px_1fr_auto] gap-3 border-b border-[var(--line)] px-5 py-3.5 last:border-b-0">
                <i className="mt-[7px] h-2.5 w-2.5 rounded-full" style={{ background: e.kind === "error" ? "#b42318" : AGENT_COLOR[e.agent] ?? "var(--ink)" }} />
                <div className="min-w-0">
                  <div className="text-[14px] font-semibold">{e.agent}</div>
                  <div className={`text-[14.5px] ${e.kind === "error" ? "text-[#b42318]" : "text-[var(--muted)]"}`}>{e.message}</div>
                </div>
                <time className="mono !normal-case !text-[11px]">
                  {new Date(e.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                </time>
              </li>
            ))}
          </ul>
        </section>

        {/* deliverables */}
        <section className="card overflow-hidden">
          <div className="flex flex-wrap items-center gap-2 border-b border-[var(--line)] px-5 py-3">
            <b className="mr-auto">Deliverables</b>
            {kinds.map((k) => (
              <button key={k} onClick={() => setTab(k)}
                className={`cursor-pointer rounded-[5px] border px-3 py-1.5 text-[13px] font-semibold ${active === k ? "border-[var(--ink)] bg-[var(--ink)] text-[var(--bg)]" : "border-[var(--line)]"}`}>
                {TAB_LABEL[k] ?? k}{latest.get(k)!.version > 1 ? ` v${latest.get(k)!.version}` : ""}
              </button>
            ))}
          </div>
          <div className="p-5 sm:p-6">
            {!active && <p className="text-[var(--muted)]">The research file appears here as soon as it is ready.</p>}
            {active === "research" && <ResearchView content={latest.get("research")!.content} />}
            {active === "strategy" && <StrategyView content={latest.get("strategy")!.content} />}
            {active === "style" && style && (
              <StyleView content={style.content} businessName={project.business_name} actionLabel={strategy?.primary_action?.label} />
            )}
            {active === "copy" && <CopyView content={latest.get("copy")!.content} />}
          </div>
        </section>
      </div>
    </>
  );
}
