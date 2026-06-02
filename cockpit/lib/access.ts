export const defaultFoundingManagerEmails = [
  "raminhoodeh@gmail.com",
  "troycookecareer@gmail.com",
  "akber.ali@hotmail.co.uk",
  "isioras@yahoo.co.uk",
  "danmerdad@hotmail.co.uk"
];

export function foundingManagerAllowlist(): string[] {
  const configured =
    process.env.QADAM_FOUNDING_MANAGER_ALLOWLIST ??
    process.env.NEXT_PUBLIC_QADAM_FOUNDING_MANAGER_ALLOWLIST;

  if (!configured) {
    return defaultFoundingManagerEmails;
  }

  return configured
    .split(",")
    .map((email) => email.trim().toLowerCase())
    .filter(Boolean);
}

export function isFoundingManager(email: string | null | undefined): boolean {
  if (!email) {
    return false;
  }

  return foundingManagerAllowlist().includes(email.toLowerCase());
}
