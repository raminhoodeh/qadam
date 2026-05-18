import { loginAction } from "./actions";
import { supabaseAuthConfigured } from "../../lib/supabase-auth";

type LoginPageProps = {
  searchParams?: Promise<{
    error?: string;
    message?: string;
    next?: string;
    email?: string;
  }>;
};

const errorCopy: Record<string, string> = {
  "supabase-not-configured": "Add Supabase URL and publishable key before logging in.",
  "missing-fields": "Enter both email and password.",
  "invalid_credentials": "Supabase rejected those credentials.",
  "missing_session": "Supabase did not return a session.",
  "not-allowlisted": "That email is signed in but not allowlisted for Qadam."
};

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const params = (await searchParams) ?? {};
  const configured = supabaseAuthConfigured();
  const next = params.next ?? "/dashboard";
  const error = params.error ? errorCopy[params.error] ?? "Login failed." : null;
  const message = params.message === "check-email" ? "Check your email to confirm the Supabase account, then log in." : null;

  return (
    <main className="authShell">
      <section className="authPanel">
        <div>
          <p className="eyebrow">Qadam Cockpit</p>
          <h1>Founding Fund Manager Login</h1>
          <p className="mutedCopy">
            Supabase handles identity. Qadam still checks the founding Fund Manager allowlist before opening the System Map.
          </p>
        </div>

        <form className="authForm mapNode" action={loginAction}>
          <input name="next" type="hidden" value={next} />
          <p className="tileLabel">Supabase Auth</p>
          <h2>Email and password</h2>
          {!configured ? (
            <p className="formStatus error">Add Supabase environment values before logging in.</p>
          ) : null}
          {error ? <p className="formStatus error">{error}</p> : null}
          {message ? <p className="formStatus registered">{message}</p> : null}
          <label>
            <span>Email</span>
            <input name="email" type="email" autoComplete="email" required />
          </label>
          <label>
            <span>Password</span>
            <input name="password" type="password" autoComplete="current-password" required />
          </label>
          <button className="settingsLink primaryAction" type="submit" disabled={!configured}>
            Login
          </button>
          <a className="mutedCopy" href="/sign-up">Create an allowlisted account</a>
        </form>
      </section>
    </main>
  );
}
