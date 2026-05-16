import { UserButton } from "@clerk/nextjs";
import { currentUser } from "@clerk/nextjs/server";
import { isFoundingManager } from "../../lib/access";

function primaryEmail(user: Awaited<ReturnType<typeof currentUser>>): string | null {
  return user?.primaryEmailAddress?.emailAddress ?? user?.emailAddresses[0]?.emailAddress ?? null;
}

export default function SettingsPage() {
  return <SettingsContent />;
}

async function SettingsContent() {
  const clerkConfigured = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY && process.env.CLERK_SECRET_KEY);
  if (!clerkConfigured) {
    return (
      <main className="shell">
        <section className="topbar">
          <div>
            <p className="eyebrow">Settings</p>
            <h1>Login Not Configured</h1>
          </div>
          <a className="settingsLink" href="/sign-in">Set Up Login</a>
        </section>
        <section className="notePanel accessPanel">
          <p className="sectionLabel">Clerk keys required</p>
          <h2>Add Clerk keys before opening protected settings.</h2>
          <p>Set NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY and CLERK_SECRET_KEY in the cockpit environment.</p>
        </section>
      </main>
    );
  }

  const user = await currentUser();
  const email = primaryEmail(user);
  if (!isFoundingManager(email)) {
    return (
      <main className="shell">
        <section className="topbar">
          <div>
            <p className="eyebrow">Settings</p>
            <h1>Access Pending</h1>
          </div>
          <UserButton afterSignOutUrl="/" />
        </section>
        <section className="notePanel accessPanel">
          <p className="sectionLabel">Founding Fund Manager allowlist</p>
          <h2>This account cannot access cockpit settings.</h2>
          <p>Signed-in email: {email ?? "unknown"}.</p>
        </section>
      </main>
    );
  }

  return (
    <main className="shell">
      <section className="topbar">
        <div>
          <p className="eyebrow">Settings</p>
          <h1>Runtime</h1>
        </div>
        <div className="userActions">
          <a className="settingsLink" href="/dashboard">Dashboard</a>
          <UserButton afterSignOutUrl="/" />
        </div>
      </section>

      <section className="settingsList">
        <div>
          <p>Auth</p>
          <strong>Clerk single-user account</strong>
        </div>
        <div>
          <p>Health</p>
          <strong>{process.env.NEXT_PUBLIC_QADAM_ORCHESTRATOR_URL ?? "http://localhost:8717"}</strong>
        </div>
        <div>
          <p>Mode</p>
          <strong>Local-first hybrid</strong>
        </div>
      </section>
    </main>
  );
}
