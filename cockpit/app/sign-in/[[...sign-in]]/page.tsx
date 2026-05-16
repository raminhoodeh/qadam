import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  const clerkConfigured = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

  return (
    <main className="authShell">
      <section className="authPanel">
        <div>
          <p className="eyebrow">Qadam Cockpit</p>
          <h1>Founding Fund Manager Login</h1>
          <p className="mutedCopy">
            Access is limited to the founding oversight group. Successful login opens the System Map.
          </p>
        </div>
        {clerkConfigured ? (
          <SignIn
            routing="path"
            path="/sign-in"
            signUpUrl="/sign-up"
            fallbackRedirectUrl="/dashboard"
          />
        ) : (
          <div className="mapNode">
            <p className="tileLabel">Clerk not configured</p>
            <h2>Add Clerk keys before using login.</h2>
            <p className="mutedCopy">
              Set NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY and CLERK_SECRET_KEY in the cockpit environment.
            </p>
          </div>
        )}
      </section>
    </main>
  );
}
