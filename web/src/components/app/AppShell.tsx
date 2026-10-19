"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import { Logo } from "@/components/site/Chrome";
import { api, auth, DEV_LOGIN } from "@/lib/api";

/** Wraps every signed-in page. Shows a sign-in panel when there is no token. */
export default function AppShell({ children }: { children: ReactNode }) {
  const [signedIn, setSignedIn] = useState<boolean | null>(null);

  useEffect(() => {
    // Session storage is only readable after hydration.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSignedIn(Boolean(auth.get()));
  }, []);

  return (
    <>
      <header className="border-b border-[var(--line)]">
        <nav className="wrap flex h-16 items-center justify-between gap-4">
          <Logo />
          {signedIn && (
            <div className="flex items-center gap-3 whitespace-nowrap text-[15px] sm:gap-5">
              <Link href="/app" className="hidden text-[var(--muted)] no-underline hover:text-[var(--ink)] sm:inline">Your projects</Link>
              <Link href="/app/new" className="btn btn-primary !px-4 !py-2 !text-sm">New project</Link>
              <button
                className="cursor-pointer text-[var(--muted)] hover:text-[var(--ink)]"
                onClick={() => { auth.clear(); setSignedIn(false); }}
              >
                Sign out
              </button>
            </div>
          )}
        </nav>
      </header>
      <main className="wrap pb-24 pt-10">
        {signedIn === null ? null : signedIn ? children : <SignIn onDone={() => setSignedIn(true)} />}
      </main>
    </>
  );
}

function SignIn({ onDone }: { onDone: () => void }) {
  const [email, setEmail] = useState("dev@example.com");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  return (
    <div className="mx-auto mt-16 max-w-[440px]">
      <h1 className="text-[40px]">Sign in</h1>
      {DEV_LOGIN ? (
        <form
          className="card mt-8 flex flex-col gap-4 p-6"
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            setError(null);
            try {
              const { access_token } = await api.devLogin(email);
              auth.set(access_token);
              onDone();
            } catch (err) {
              setError(err instanceof Error ? err.message : "Sign in failed");
            } finally {
              setBusy(false);
            }
          }}
        >
          <p className="text-[15px] text-[var(--muted)]">
            Development sign-in. No password: any email gets its own test account on this machine.
          </p>
          <label className="flex flex-col gap-1.5 text-sm font-semibold">
            Email
            <input className="field" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          {error && <p className="text-sm text-[#b42318]">{error}</p>}
          <button className="btn btn-primary justify-center" disabled={busy}>
            {busy ? "Signing in" : "Sign in as developer"}
          </button>
        </form>
      ) : (
        <p className="mt-6 text-[var(--muted)]">Accounts open soon.</p>
      )}
    </div>
  );
}
