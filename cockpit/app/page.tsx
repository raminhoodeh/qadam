import { currentSupabaseUser } from "../lib/supabase-auth";

export default async function HomePage() {
  const user = await currentSupabaseUser();

  return (
    <main className="landingPage">
      <section className="landingHero">
        <video className="landingVideo" autoPlay muted loop playsInline>
          <source
            src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260217_030345_246c0224-10a4-422c-b324-070b7c0eceda.mp4"
            type="video/mp4"
          />
        </video>
        <div className="landingOverlay" />
        <nav className="landingNav" aria-label="Qadam navigation">
          <a className="landingLogo" href="/" aria-label="Qadam home">
            <img src="/logo.png" alt="QADAM" />
          </a>
          <div className="landingActions">
            <a className="glassButton secondaryGlass" href="/whitepaper">
              Read Whitepaper
            </a>
            <a className="glassButton" href={user ? "/dashboard" : "/login"}>
              {user ? "Dashboard" : "Login"}
            </a>
          </div>
        </nav>

        <div className="landingContent">
          <div className="landingBadge">
            <span />
            Early access available from July 23, 2026
          </div>
          <h1>A hedge fund team that fits inside your laptop.</h1>
          <p>
            Qadam is a boutique macro intelligence fund running on a hybrid system of a Python script [COO], a local
            LLM [Research Analyst], a frontier LLM [Strategy Lead], and a quantum computer [Head of Quant]. 500+ live
            data feeds across 5 intelligence pipelines. One overseeing Fund Manager [you].
          </p>
          <p>
            Qadam operates on a self-imposed trading strategy based on a deep and continuous understanding of its own
            cognition, latency and data quality. Phase 1 is optimised for prediction markets, crude oil, defence,
            silver, and semiconductors.
          </p>
          <div className="landingCtas">
            <a className="glassButton heroGlass" href="https://wa.link/s1pqwy" target="_blank" rel="noreferrer">
              Join Waitlist
            </a>
            <a className="plainHeroLink" href={user ? "/dashboard" : "/login"}>
              {user ? "Open cockpit" : "Fund Manager login"}
            </a>
          </div>
        </div>
      </section>
    </main>
  );
}
