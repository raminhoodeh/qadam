import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { isFoundingManager } from "./access";

const ACCESS_COOKIE = "qadam_sb_access_token";
const REFRESH_COOKIE = "qadam_sb_refresh_token";

type SupabaseUser = {
  id: string;
  email?: string;
};

type AuthResult = {
  email: string;
  userId: string;
};

function supabaseUrl(): string {
  return (process.env.NEXT_PUBLIC_SUPABASE_URL ?? "").replace(/\/$/, "");
}

function supabaseKey(): string {
  return process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";
}

export function supabaseAuthConfigured(): boolean {
  return Boolean(supabaseUrl() && supabaseKey());
}

function cookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge
  };
}

async function setSessionCookies(accessToken: string, refreshToken?: string, expiresIn?: number) {
  const jar = await cookies();
  jar.set(ACCESS_COOKIE, accessToken, cookieOptions(expiresIn ?? 60 * 60));
  if (refreshToken) {
    jar.set(REFRESH_COOKIE, refreshToken, cookieOptions(60 * 60 * 24 * 30));
  }
}

export async function clearSupabaseSession() {
  const jar = await cookies();
  jar.delete(ACCESS_COOKIE);
  jar.delete(REFRESH_COOKIE);
}

async function supabaseFetch(path: string, init: RequestInit) {
  const url = supabaseUrl();
  const key = supabaseKey();
  if (!url || !key) {
    throw new Error("supabase_not_configured");
  }

  return fetch(`${url}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      apikey: key,
      "Content-Type": "application/json",
      ...(init.headers ?? {})
    }
  });
}

export async function signInWithPassword(email: string, password: string) {
  const response = await supabaseFetch("/auth/v1/token?grant_type=password", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });

  if (!response.ok) {
    return { ok: false, reason: "invalid_credentials" };
  }

  const payload = await response.json();
  if (!payload.access_token) {
    return { ok: false, reason: "missing_session" };
  }

  await setSessionCookies(payload.access_token, payload.refresh_token, payload.expires_in);
  return { ok: true, reason: "signed_in" };
}

export async function signUpWithPassword(email: string, password: string) {
  if (!isFoundingManager(email)) {
    return { ok: false, reason: "not_allowlisted" };
  }

  const response = await supabaseFetch("/auth/v1/signup", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });

  if (!response.ok) {
    return { ok: false, reason: "signup_failed" };
  }

  const payload = await response.json();
  if (payload.access_token) {
    await setSessionCookies(payload.access_token, payload.refresh_token, payload.expires_in);
    return { ok: true, reason: "signed_in" };
  }

  return { ok: true, reason: "check_email" };
}

export async function currentSupabaseUser(): Promise<AuthResult | null> {
  if (!supabaseAuthConfigured()) {
    return null;
  }

  const jar = await cookies();
  const accessToken = jar.get(ACCESS_COOKIE)?.value;
  if (!accessToken) {
    return null;
  }

  const response = await supabaseFetch("/auth/v1/user", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  });

  if (!response.ok) {
    return null;
  }

  const user = (await response.json()) as SupabaseUser;
  if (!user.email) {
    return null;
  }

  return { email: user.email, userId: user.id };
}

export async function verifySupabaseAccessToken(accessToken: string): Promise<AuthResult | null> {
  if (!supabaseAuthConfigured() || !accessToken) {
    return null;
  }

  const response = await supabaseFetch("/auth/v1/user", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${accessToken}`
    }
  });

  if (!response.ok) {
    return null;
  }

  const user = (await response.json()) as SupabaseUser;
  if (!user.email) {
    return null;
  }

  return { email: user.email, userId: user.id };
}

export async function currentSupabaseUserFromRequest(request: Request): Promise<AuthResult | null> {
  const authorization = request.headers.get("authorization") ?? "";
  const [scheme, token] = authorization.split(/\s+/, 2);
  if (scheme?.toLowerCase() === "bearer" && token) {
    return verifySupabaseAccessToken(token);
  }

  return currentSupabaseUser();
}

export async function requireFundManager(): Promise<AuthResult> {
  if (!supabaseAuthConfigured()) {
    redirect("/login?error=supabase-not-configured" as never);
  }

  const user = await currentSupabaseUser();
  if (!user) {
    redirect("/login" as never);
  }

  if (!isFoundingManager(user.email)) {
    redirect(`/login?error=not-allowlisted&email=${encodeURIComponent(user.email)}` as never);
  }

  return user;
}
