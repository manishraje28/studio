import type { ProjectStatus } from "@/lib/api";

export const STATUS_LABEL: Record<ProjectStatus, string> = {
  briefed: "Brief received",
  researching: "Researching",
  strategy: "Planning pages",
  design: "Art direction",
  awaiting_approval: "Waiting for your approval",
  copy: "Writing copy",
  building: "Building",
  qa: "Testing",
  preview: "Preview ready",
  live: "Live",
  failed: "Stopped",
};

/** The stages shown on the project page, in order. */
export const STAGES: { status: ProjectStatus; label: string }[] = [
  { status: "researching", label: "Research" },
  { status: "strategy", label: "Strategy" },
  { status: "design", label: "Art direction" },
  { status: "copy", label: "Copy" },
  { status: "building", label: "Build" },
  { status: "qa", label: "Testing" },
  { status: "preview", label: "Your review" },
];

const ORDER: ProjectStatus[] = ["briefed", "researching", "strategy", "design", "awaiting_approval", "copy", "building", "qa", "preview", "live"];
// Waiting for approval still belongs to the art direction stage on the rail.
export const stageIndex = (s: ProjectStatus) => ORDER.indexOf(s === "awaiting_approval" ? "design" : s);
