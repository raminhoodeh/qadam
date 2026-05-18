import { readFile } from "node:fs/promises";
import path from "node:path";
import { isFoundingManager } from "../../../lib/access";
import { currentSupabaseUserFromRequest } from "../../../lib/supabase-auth";

export const dynamic = "force-dynamic";

const STATUS_FILE = "cockpit-status.json";
const SIGNATURE_FILE = "cockpit-status.signature.json";
const READ_METHODS = "GET, HEAD";
const RATE_LIMIT_WINDOW_MS = 60_000;
const RATE_LIMIT_MAX = Number(process.env.QADAM_STATUS_BRIDGE_RATE_LIMIT_PER_MINUTE ?? "60");

type RateBucket = {
  count: number;
  resetAt: number;
};

type StatusSource = {
  statusPath: string;
  signaturePath: string;
  label: string;
};

const rateBuckets = new Map<string, RateBucket>();

function bridgeHeaders(extra?: HeadersInit): Headers {
  const headers = new Headers({
    "Cache-Control": "no-store, max-age=0",
    "X-Qadam-Bridge": "read-only",
    "X-Qadam-Browser-Authority": "read-only",
    "X-Qadam-Broker-Write-Route": "false"
  });
  if (extra) {
    new Headers(extra).forEach((value, key) => {
      headers.set(key, value);
    });
  }
  return headers;
}

function jsonResponse(payload: unknown, init?: ResponseInit): Response {
  return Response.json(payload, {
    ...init,
    headers: bridgeHeaders(init?.headers)
  });
}

function methodNotAllowed(): Response {
  return jsonResponse(
    {
      error: "method_not_allowed",
      allowed_methods: ["GET", "HEAD"],
      broker_write_route: false
    },
    {
      status: 405,
      headers: {
        Allow: READ_METHODS
      }
    }
  );
}

function requestKey(request: Request): string {
  const forwardedFor = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim();
  return forwardedFor || request.headers.get("x-real-ip") || "local";
}

function rateLimit(request: Request): Response | null {
  const now = Date.now();
  const key = requestKey(request);
  const bucket = rateBuckets.get(key);
  if (!bucket || bucket.resetAt <= now) {
    rateBuckets.set(key, { count: 1, resetAt: now + RATE_LIMIT_WINDOW_MS });
    return null;
  }
  bucket.count += 1;
  if (bucket.count <= RATE_LIMIT_MAX) {
    return null;
  }
  return jsonResponse(
    {
      error: "rate_limited",
      retry_after_seconds: Math.ceil((bucket.resetAt - now) / 1000)
    },
    {
      status: 429,
      headers: {
        "Retry-After": String(Math.ceil((bucket.resetAt - now) / 1000))
      }
    }
  );
}

async function authorize(request: Request): Promise<Response | null> {
  const user = await currentSupabaseUserFromRequest(request);
  if (!user) {
    return jsonResponse({ error: "unauthenticated" }, { status: 401 });
  }
  if (!isFoundingManager(user.email)) {
    return jsonResponse({ error: "not_allowlisted" }, { status: 403 });
  }
  return null;
}

function candidateSources(): StatusSource[] {
  const configured = process.env.QADAM_COCKPIT_STATUS_PATH;
  const candidates = [
    configured,
    path.resolve(process.cwd(), "..", "data", "runtime", STATUS_FILE),
    path.resolve(process.cwd(), "..", "landing-page-repo", "status", STATUS_FILE),
    path.resolve(process.cwd(), "public", "status", STATUS_FILE)
  ].filter(Boolean) as string[];

  return candidates.map((statusPath) => ({
    statusPath,
    signaturePath: path.join(path.dirname(statusPath), SIGNATURE_FILE),
    label: statusPath.includes(`${path.sep}data${path.sep}runtime${path.sep}`)
      ? "runtime_snapshot"
      : statusPath.includes(`${path.sep}landing-page-repo${path.sep}`)
        ? "landing_snapshot"
        : "configured_snapshot"
  }));
}

async function readSnapshot(): Promise<{ payload: unknown; signature: Record<string, unknown> | null; source: StatusSource } | null> {
  for (const source of candidateSources()) {
    try {
      const payload = JSON.parse(await readFile(source.statusPath, "utf8")) as unknown;
      let signature: Record<string, unknown> | null = null;
      try {
        signature = JSON.parse(await readFile(source.signaturePath, "utf8")) as Record<string, unknown>;
      } catch {
        signature = null;
      }
      return { payload, signature, source };
    } catch {
      continue;
    }
  }
  return null;
}

function validatePublicStatus(payload: unknown): string | null {
  if (!payload || typeof payload !== "object") return "invalid_payload";
  const status = payload as Record<string, any>;
  if (status.schema_version !== 1) return "schema_version_mismatch";
  if (status.mode !== "paper") return "paper_mode_required";
  if (status.d1_snapshot?.read_only !== true) return "snapshot_not_read_only";
  if (status.d1_snapshot?.public_safe !== true) return "snapshot_not_public_safe";
  if (status.d1_snapshot?.local_orchestrator_exposed !== false) return "orchestrator_exposed";
  if (status.capital?.live_capital_enabled !== false) return "live_capital_enabled";
  if (status.live_bridge?.read_only !== true) return "bridge_not_read_only";
  if (status.live_bridge?.write_authority !== false) return "bridge_write_authority_enabled";
  if (status.live_bridge?.broker_write_route !== false) return "bridge_broker_write_route_enabled";
  if (status.live_bridge?.local_orchestrator_exposed !== false) return "bridge_orchestrator_exposed";
  return null;
}

async function statusResponse(request: Request, headOnly = false): Promise<Response> {
  const limited = rateLimit(request);
  if (limited) return limited;

  const authError = await authorize(request);
  if (authError) return authError;

  const snapshot = await readSnapshot();
  if (!snapshot) {
    return jsonResponse({ error: "snapshot_unavailable" }, { status: 503 });
  }

  const validationError = validatePublicStatus(snapshot.payload);
  if (validationError) {
    return jsonResponse({ error: validationError }, { status: 503 });
  }

  const headers = bridgeHeaders({
    "X-Qadam-Status-Source": snapshot.source.label,
    "X-Qadam-Status-Signature": String(snapshot.signature?.signature ?? "missing"),
    "X-Qadam-Status-Signature-Mode": String(snapshot.signature?.algorithm ?? "missing")
  });

  if (headOnly) {
    return new Response(null, { status: 200, headers });
  }

  return Response.json(snapshot.payload, { status: 200, headers });
}

export async function GET(request: Request): Promise<Response> {
  return statusResponse(request);
}

export async function HEAD(request: Request): Promise<Response> {
  return statusResponse(request, true);
}

export async function POST(): Promise<Response> {
  return methodNotAllowed();
}

export async function PUT(): Promise<Response> {
  return methodNotAllowed();
}

export async function PATCH(): Promise<Response> {
  return methodNotAllowed();
}

export async function DELETE(): Promise<Response> {
  return methodNotAllowed();
}
