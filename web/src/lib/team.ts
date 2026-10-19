export type Agent = {
  role: string;
  color: string;
  doing: string;
  job: string;
  handsOver: string;
  icon: string;
};

// Colors mirror --r1..--r6 in globals.css; the 3D scene needs literal values.
export const TEAM: Agent[] = [
  {
    role: "Researcher",
    color: "#e98a6b",
    doing: "reading reviews",
    job: "Reads your Google reviews, your current site and nearby competitors.",
    handsOver: "Research file with sources",
    icon: '<circle cx="10" cy="10" r="6"/><path d="M15 15l5 5"/>',
  },
  {
    role: "Strategist",
    color: "#8fc4b5",
    doing: "planning pages",
    job: "Decides who the site is for, which pages you need and the one action visitors should take.",
    handsOver: "Sitemap and page goals",
    icon: '<path d="M4 18l5-6 4 3 7-9"/><path d="M15 6h5v5"/>',
  },
  {
    role: "Art director",
    color: "#e8b84a",
    doing: "picking colours",
    job: "Chooses colours, type and the one or two visual ideas that make the site yours.",
    handsOver: "Style tile for approval",
    icon: '<circle cx="12" cy="12" r="8"/><circle cx="9" cy="9" r="1.4"/><circle cx="15" cy="9" r="1.4"/><circle cx="9" cy="15" r="1.4"/>',
  },
  {
    role: "Copywriter",
    color: "#a996d6",
    doing: "writing copy",
    job: "Writes every page in your voice. Every claim about your business comes from the research file.",
    handsOver: "Page copy",
    icon: '<path d="M4 20l4-1 11-11-3-3L5 16z"/><path d="M14 6l3 3"/>',
  },
  {
    role: "Developer",
    color: "#7fa7d9",
    doing: "building pages",
    job: "Builds the site from the approved design and copy, then wires up forms and analytics.",
    handsOver: "Preview link and code",
    icon: '<path d="M8 7l-5 5 5 5M16 7l5 5-5 5"/>',
  },
  {
    role: "QA critic",
    color: "#e391ad",
    doing: "testing on phones",
    job: "Tests on phones, checks speed, accessibility and links, and sends problems back to the right agent.",
    handsOver: "Test report",
    icon: '<path d="M5 12l4 4 10-10"/>',
  },
];
