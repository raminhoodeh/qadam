import { SignInButton, SignedIn, SignedOut, UserButton } from "@clerk/nextjs";

export default function CockpitEntryPage() {
  const clerkConfigured = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

  return (
    <main className="shell entryShell">
      <section className="topbar">
        <div>
          <p className="eyebrow">Qadam Cockpit</p>
          <h1>Fund Manager Access</h1>
        </div>
        {clerkConfigured ? (
          <>
            <SignedOut>
              <SignInButton mode="redirect" forceRedirectUrl="/dashboard">
                <button className="settingsLink" type="button">Login</button>
              </SignInButton>
            </SignedOut>
            <SignedIn>
              <div className="userActions">
                <a className="settingsLink" href="/dashboard">Dashboard</a>
                <UserButton afterSignOutUrl="/" />
              </div>
            </SignedIn>
          </>
        ) : (
          <a className="settingsLink" href="/sign-in">Login</a>
        )}
      </section>

      <section className="statusBand registered">
        <div>
          <span className="statusDot registered" />
          <p>PAPER MODE · GBP 1000 trial · Founding access only</p>
        </div>
        <p>System Map, health, sources, modules, shadow intelligence, and governance notes.</p>
      </section>

      <section className="entryGrid">
        <article className="mapNode">
          <p className="tileLabel">Access model</p>
          <h2>Ramin, Troy, Ion now. Akber and Anas pending emails.</h2>
          <p className="mutedCopy">
            Clerk handles identity. Qadam applies its own founding Fund Manager allowlist before showing the cockpit.
          </p>
        </article>
        <article className="mapNode">
          <p className="tileLabel">First view after login</p>
          <h2>System Map</h2>
          <p className="mutedCopy">
            The dashboard shows the COO, Research Analyst, Strategy Lead, Head of Quant, data feeds,
            local stores, execution rails, and uptime state.
          </p>
        </article>
        <article className="mapNode">
          <p className="tileLabel">Operating boundary</p>
          <h2>Shadow intelligence only</h2>
          <p className="mutedCopy">
            The current cockpit can observe provider readiness and proposed signals. It cannot place trades.
          </p>
        </article>
      </section>
    </main>
  );
}
