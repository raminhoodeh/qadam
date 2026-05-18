export default function HealthzPage() {
  return (
    <main className="shell">
      <section className="topbar">
        <div>
          <p className="eyebrow">Qadam</p>
          <h1>Deployment Health</h1>
        </div>
        <a className="settingsLink" href="/login">Login</a>
      </section>
      <section className="statusBand registered">
        <div>
          <span className="statusDot registered" />
          <p>Qadam cockpit deployment is serving Next.js routes.</p>
        </div>
        <p>Route check: /healthz</p>
      </section>
    </main>
  );
}
