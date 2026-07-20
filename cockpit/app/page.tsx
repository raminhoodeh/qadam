import { currentSupabaseUser } from "../lib/supabase-auth";

const whitepaperUrl =
  "https://www.notion.so/Qadam-Specifications-v3-3566fe2ecf37800abef8c5c717cc6656?source=copy_link";
const whatsappEnquiryMessage =
  `Hey Ramin, I'd like your advice on how to set up Qadam at our hedge fund or boutique investment firm. ` +
  `In the meantime, I'll check out the white paper and let you know what I think!\n\n${whitepaperUrl}`;
const whatsappEnquiryUrl = `https://wa.me/447852890444?text=${encodeURIComponent(whatsappEnquiryMessage)}`;

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
              Read White Paper
            </a>
            {user ? (
              <a className="glassButton" href="/dashboard">
                Dashboard
              </a>
            ) : null}
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
            <a className="glassButton heroGlass" href={whatsappEnquiryUrl} target="_blank" rel="noreferrer">
              Join Waitlist
            </a>
            <a className="glassButton secondaryGlass" href="/whitepaper">
              Read White Paper
            </a>
          </div>
        </div>
      </section>
    </main>
  );
}
