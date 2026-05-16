import { getCockpitHealth } from "../../../lib/health";

export async function GET() {
  const health = await getCockpitHealth();
  return Response.json({
    service: "qadam-cockpit",
    ...health
  });
}
