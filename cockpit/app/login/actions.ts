"use server";

import { redirect } from "next/navigation";
import { clearSupabaseSession, signInWithPassword, signUpWithPassword } from "../../lib/supabase-auth";

function cleanNext(value: FormDataEntryValue | null): string {
  const next = typeof value === "string" ? value : "/dashboard";
  return next.startsWith("/") && !next.startsWith("//") ? next : "/dashboard";
}

export async function loginAction(formData: FormData) {
  const email = String(formData.get("email") ?? "").trim().toLowerCase();
  const password = String(formData.get("password") ?? "");
  const next = cleanNext(formData.get("next"));

  if (!email || !password) {
    redirect(`/login?error=missing-fields&next=${encodeURIComponent(next)}` as never);
  }

  const result = await signInWithPassword(email, password);
  if (!result.ok) {
    redirect(`/login?error=${result.reason}&next=${encodeURIComponent(next)}` as never);
  }

  redirect(next as never);
}

export async function signUpAction(formData: FormData) {
  const email = String(formData.get("email") ?? "").trim().toLowerCase();
  const password = String(formData.get("password") ?? "");

  if (!email || !password) {
    redirect("/sign-up?error=missing-fields" as never);
  }

  const result = await signUpWithPassword(email, password);
  if (!result.ok) {
    redirect(`/sign-up?error=${result.reason}` as never);
  }

  if (result.reason === "check_email") {
    redirect("/login?message=check-email" as never);
  }

  redirect("/dashboard" as never);
}

export async function signOutAction() {
  await clearSupabaseSession();
  redirect("/login" as never);
}
