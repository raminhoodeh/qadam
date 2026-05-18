import { signUpAction } from "../../login/actions";
import { supabaseAuthConfigured } from "../../../lib/supabase-auth";

type SignUpPageProps = {
  searchParams?: Promise<{
    error?: string;
  }>;
};

const errorCopy: Record<string, string> = {
  "missing-fields": "Enter both email and password.",
  "not_allowlisted": "That email is not in the founding Fund Manager allowlist.",
  "signup_failed": "Supabase could not create that account."
};

export default async function SignUpPage({ searchParams }: SignUpPageProps) {
  const params = (await searchParams) ?? {};
  const configured = supabaseAuthConfigured();
  const error = params.error ? errorCopy[params.error] ?? "Signup failed." : null;

  return (
    <main className="authShell">
      <section className="authPanel">
        <div>
          <p className="eyebrow">Qadam Cockpit</p>
          <h1>Create Access</h1>
          <p className="mutedCopy">
            Account creation is restricted to the founding Fund Manager allowlist.
          </p>
        </div>

        <form className="authForm mapNode" action={signUpAction}>
          <p className="tileLabel">Supabase Auth</p>
          <h2>Allowlisted account</h2>
          {!configured ? (
            <p className="formStatus error">Add Supabase environment values before creating access.</p>
          ) : null}
          {error ? <p className="formStatus error">{error}</p> : null}
          <label>
            <span>Email</span>
            <input name="email" type="email" autoComplete="email" required />
          </label>
          <label>
            <span>Password</span>
            <input name="password" type="password" autoComplete="new-password" required />
          </label>
          <button className="settingsLink primaryAction" type="submit" disabled={!configured}>
            Create Account
          </button>
          <a className="mutedCopy" href="/login">Back to login</a>
        </form>
      </section>
    </main>
  );
}
