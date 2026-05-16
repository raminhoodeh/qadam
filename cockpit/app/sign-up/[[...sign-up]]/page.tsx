import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  const clerkConfigured = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

  return (
    <main className="authShell">
      <section className="authPanel">
        <div>
          <p className="eyebrow">Qadam Cockpit</p>
          <h1>Create Access</h1>
          <p className="mutedCopy">
            Only allowlisted founding Fund Manager emails can open the cockpit dashboard.
          </p>
        </div>
        {clerkConfigured ? (
          <SignUp
            routing="path"
            path="/sign-up"
            signInUrl="/sign-in"
            fallbackRedirectUrl="/dashboard"
          />
        ) : (
          <div className="mapNode">
            <p className="tileLabel">Clerk not configured</p>
            <h2>Add Clerk keys before creating access.</h2>
            <p className="mutedCopy">
              Set NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY and CLERK_SECRET_KEY in the cockpit environment.
            </p>
          </div>
        )}
      </section>
    </main>
  );
}
