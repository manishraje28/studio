import Link from "next/link";

export function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2.5 no-underline serif text-[21px] font-bold">
      <svg viewBox="0 0 32 32" width="28" height="28" aria-hidden>
        <rect width="32" height="32" rx="7" fill="var(--accent)" />
        <circle cx="16" cy="13" r="6" fill="var(--bg)" />
        <rect x="8" y="21" width="16" height="5" rx="2.5" fill="var(--bg)" />
      </svg>
      studio
    </Link>
  );
}

export function Header() {
  return (
    <header className="sticky top-0 z-30 border-b border-[var(--line)] bg-[color-mix(in_srgb,var(--bg)_86%,transparent)] backdrop-blur-md">
      <nav className="wrap flex h-16 items-center justify-between gap-4">
        <Logo />
        <div className="hidden gap-7 text-[15px] text-[var(--muted)] md:flex">
          <Link href="/#team" className="no-underline hover:text-[var(--ink)]">The team</Link>
          <Link href="/#floor" className="no-underline hover:text-[var(--ink)]">How it works</Link>
          <Link href="/#pricing" className="no-underline hover:text-[var(--ink)]">Pricing</Link>
          <Link href="/#faq" className="no-underline hover:text-[var(--ink)]">FAQ</Link>
        </div>
        <Link href="/#start" className="btn btn-primary !px-4 !py-2.5 !text-sm">Start a project</Link>
      </nav>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="wrap flex flex-wrap justify-between gap-6 pb-14 pt-12 text-sm text-[var(--muted)]">
      <span>© 2026 Studio</span>
      <nav className="flex flex-wrap gap-6">
        <Link href="/#team" className="no-underline hover:text-[var(--ink)]">The team</Link>
        <Link href="/#pricing" className="no-underline hover:text-[var(--ink)]">Pricing</Link>
        <Link href="/privacy" className="no-underline hover:text-[var(--ink)]">Privacy policy</Link>
        <Link href="/terms" className="no-underline hover:text-[var(--ink)]">Terms and conditions</Link>
        <a href="mailto:hello@studio.example" className="no-underline hover:text-[var(--ink)]">Contact</a>
      </nav>
    </footer>
  );
}
