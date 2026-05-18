import { signOutAction } from "../login/actions";
import { requireFundManager, supabaseAuthConfigured } from "../../lib/supabase-auth";

export default function SettingsPage() {
  return <SettingsContent />;
}

async function SettingsContent() {
  if (!supabaseAuthConfigured()) {
    return (
      <main className="shell">
        <section className="topbar">
          <div>
            <p className="eyebrow">Settings</p>
            <h1>Login Not Configured</h1>
          </div>
          <a className="settingsLink" href="/login">Set Up Login</a>
        </section>
        <section className="notePanel accessPanel">
          <p className="sectionLabel">Supabase keys required</p>
          <h2>Add Supabase URL and publishable key before opening protected settings.</h2>
          <p>Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY in the cockpit environment.</p>
        </section>
      </main>
    );
  }

  const user = await requireFundManager();

  return (
    <main className="shell">
      <section className="topbar">
        <div>
          <p className="eyebrow">Settings</p>
          <h1>Runtime</h1>
        </div>
        <div className="userActions">
          <a className="settingsLink" href="/dashboard">Dashboard</a>
          <form action={signOutAction}>
            <button className="settingsLink" type="submit">Sign Out</button>
          </form>
        </div>
      </section>

      <section className="settingsList">
        <div>
          <p>Auth</p>
          <strong>Supabase Auth allowlist</strong>
          <span>{user.email}</span>
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
