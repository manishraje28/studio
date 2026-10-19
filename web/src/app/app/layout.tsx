import type { Metadata } from "next";
import AppShell from "@/components/app/AppShell";

export const metadata: Metadata = { title: "Your projects | Studio" };

export default function AppLayout({ children }: LayoutProps<"/app">) {
  return <AppShell>{children}</AppShell>;
}
