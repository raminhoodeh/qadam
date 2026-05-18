import { getCockpitHealth } from "../../../lib/health";
import { currentSupabaseUser } from "../../../lib/supabase-auth";

export async function GET() {
  const user = await currentSupabaseUser();
  if (!user) {
    return Response.json({ error: "unauthenticated" }, { status: 401 });
  }

  const health = await getCockpitHealth();
  return Response.json({
    service: "qadam-cockpit",
    ...health
  });
}
