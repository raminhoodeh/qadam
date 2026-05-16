export default function SettingsPage() {
  return (
    <main className="shell">
      <section className="topbar">
        <div>
          <p className="eyebrow">Settings</p>
          <h1>Runtime</h1>
        </div>
        <a className="settingsLink" href="/">Dashboard</a>
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

