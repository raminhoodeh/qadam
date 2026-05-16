import { getCockpitHealth } from "../lib/health";
import type { AdapterStatus } from "../lib/health";

export const dynamic = "force-dynamic";

const pipelineLabels: Record<string, string> = {
  conflict: "Conflict",
  physical: "Physical",
  macro: "Macro",
  market: "Market",
  social: "Narrative"
};

const pipelineDetails: Record<string, string> = {
  conflict: "ACLED, GDELT, Oref",
  physical: "FIRMS, AIS, Wingbits",
  macro: "FRED, BLS, ECB",
  market: "Alpaca, Polymarket, Kalshi",
  social: "RSS, Telegram, X"
};

const knownManagerNames: Record<string, string> = {
  "raminhoodeh@gmail.com": "Ramin",
  "troycookecareer@gmail.com": "Troy",
  "isioras@yahoo.co.uk": "Ion"
};

function statusClass(status: string): string {
  const normalised = status.toLowerCase();
  if (normalised.includes("error") || normalised.includes("failed")) return "error";
  if (normalised.includes("degraded") || normalised.includes("fallback") || normalised.includes("not_running")) {
    return "degraded";
  }
  if (normalised.includes("pending") || normalised.includes("not_started")) return "pending";
  if (normalised.includes("disabled") || normalised.includes("blocked") || normalised.includes("credential_gated")) {
    return "disabled";
  }
  return "registered";
}

function labelForStatus(status: string): string {
  return status.replaceAll("_", " ");
}

function adapterTitle(adapter: AdapterStatus): string {
  return `${adapter.key.toUpperCase()} Adapter`;
}

function adapterDetail(adapter: AdapterStatus): string {
  const count =
    adapter.default_series_count ? `${adapter.default_series_count} series` :
    adapter.default_feed_count ? `${adapter.default_feed_count} feeds` :
    adapter.default_area_count ? `${adapter.default_area_count} areas` :
    adapter.source;
  const credential =
    adapter.credential_configured === false && adapter.auth !== "none" ? "credential missing" : adapter.auth.replaceAll("_", " ");
  return `${count} · trust ${adapter.trust_score.toFixed(2)} · ${credential}`;
}

export default async function DashboardPage() {
  const health = await getCockpitHealth();
  const modules = health.modules;
  const adapters = Object.values(health.adapters).sort((left, right) => left.key.localeCompare(right.key));
  const pipelines = Object.entries(health.pipeline_counts).sort(
    ([left], [right]) =>
      Object.keys(pipelineLabels).indexOf(left) - Object.keys(pipelineLabels).indexOf(right)
  );
  const resourceCount = health.resource_registry.resource_count;
  const claimCount = health.world_model.claim_count;
  const executionDisabled = health.execution_summary.write_enabled === 0;
  const sourceLine = `${health.source_count} sources · ${resourceCount} resources · ${claimCount} private claim cards · execution ${
    executionDisabled ? "disabled" : "write-enabled"
  }`;
  const heartbeatSummary = health.source_heartbeat.summary ?? {};

  const registryCards = [
    {
      title: "Resource Registry",
      count: `${resourceCount} references`,
      detail: health.resource_registry.boundary
    },
    {
      title: "World-Model Corpus",
      count: `${claimCount} claim cards`,
      detail: health.world_model.evidence_boundary
    },
    {
      title: "Governance Forum",
      count: `${health.governance_forum.comment_count} comments`,
      detail: `Visible to ${health.governance_forum.visibility.replaceAll("_", " ")}`
    },
    {
      title: "Test Ingestion Spine",
      count: health.ingestion_spine.mode,
      detail: health.ingestion_spine.boundary
    },
    {
      title: "Source Heartbeat",
      count: `${heartbeatSummary.promoted_adapter_count ?? 0} promoted`,
      detail: `${heartbeatSummary.missing_credential_source_count ?? 0} sources missing credentials · ${
        heartbeatSummary.deferred_count ?? 0
      } deferred`
    },
    ...adapters.map((adapter) => ({
      title: adapterTitle(adapter),
      count: adapter.mode.replaceAll("_", " "),
      detail: adapterDetail(adapter)
    }))
  ];

  const outputCards = [
    { title: "Evidence Trail", status: health.event_log.status, detail: health.event_log.backend ?? "event log" },
    { title: "Signal Review", status: "pending", detail: "Phase 2 shadow signals" },
    {
      title: "Broker Rail",
      status: executionDisabled ? "disabled" : "registered",
      detail: `${health.execution_summary.first_release_allowed} first-release venues`
    },
    { title: "Governance Forum", status: health.governance_forum.status, detail: "local comments" }
  ];

  const fundManagers = [
    ...health.fund_managers.allowlist_emails.map((email) => ({
      name: knownManagerNames[email] ?? email.split("@")[0],
      email,
      status: "allowlisted"
    })),
    ...health.fund_managers.pending_names.map((name) => ({
      name,
      email: "email pending",
      status: "pending"
    }))
  ];

  return (
    <main className="shell">
      <section className="topbar">
        <div>
          <p className="eyebrow">Qadam</p>
          <h1>System Map</h1>
        </div>
        <a className="settingsLink" href="/settings">Settings</a>
      </section>

      <section className={`statusBand ${statusClass(health.status)}`}>
        <div>
          <span className={`statusDot ${statusClass(health.status)}`} />
          <p>
            {labelForStatus(health.status)} · {health.mode.toUpperCase()} MODE · GBP {health.trial_balance_gbp} trial
          </p>
        </div>
        <p>{sourceLine}</p>
      </section>

      <section className="mapLayout">
        <div className="pipelineColumn">
          <p className="sectionLabel">Intelligence pipelines</p>
          {pipelines.map(([key, count]) => (
            <article className="mapNode pipelineNode" key={key}>
              <div>
                <p className="tileLabel">{pipelineLabels[key] ?? key}</p>
                <h2>{count} sources</h2>
              </div>
              <p>{pipelineDetails[key] ?? "Registered source group"}</p>
            </article>
          ))}
        </div>

        <div className="coreMap">
          <p className="sectionLabel">Hybrid fund core</p>
          <div className="nodeGrid">
            {modules.map((module) => (
              <article className="mapNode" key={module.key}>
                <div className="nodeHeader">
                  <p className="tileLabel">{module.label}</p>
                  <span className={`miniStatus ${statusClass(module.status)}`} />
                </div>
                <h2>{module.owner}</h2>
                <p>{labelForStatus(module.status)}</p>
              </article>
            ))}
          </div>
        </div>

        <div className="pipelineColumn">
          <p className="sectionLabel">Outputs</p>
          {outputCards.map((card) => (
            <article className="mapNode outputNode" key={card.title}>
              <div className="nodeHeader">
                <p className="tileLabel">{card.title}</p>
                <span className={`miniStatus ${statusClass(card.status)}`} />
              </div>
              <h2>{labelForStatus(card.status)}</h2>
              <p className="mutedCopy">{card.detail}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="liveMeta">
        <span>Health source: {health.source ?? "cockpit"}</span>
        <span>Unresolved sources: {health.unresolved_sources.length}</span>
        <span>Source map: {labelForStatus(health.source_heartbeat.status)}</span>
        <span>Offline stores: {health.local_stores.summary?.offline_services?.join(", ") || "none"}</span>
      </section>

      <section className="registryGrid">
        {registryCards.map((card) => (
          <article className="mapNode" key={card.title}>
            <p className="tileLabel">{card.title}</p>
            <h2>{card.count}</h2>
            <p className="mutedCopy">{card.detail}</p>
          </article>
        ))}
      </section>

      <section className="governanceGrid">
        <div>
          <p className="sectionLabel">Founding Fund Manager access</p>
          <div className="settingsList">
            {fundManagers.map((manager) => (
              <div key={`${manager.name}-${manager.email}`}>
                <p>{manager.status}</p>
                <h2>{manager.name}</h2>
                <span>{manager.email}</span>
              </div>
            ))}
          </div>
        </div>

        <div>
          <p className="sectionLabel">Execution venue registry</p>
          <div className="settingsList">
            {health.execution_venues.map((venue) => (
              <div key={venue.key}>
                <p>{labelForStatus(venue.mode)}</p>
                <h2>{venue.name}</h2>
                <span>{venue.account_scope} · {venue.kill_switch_status}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="notePanel">
        <p className="sectionLabel">Private evidence boundary</p>
        <h2>World-model claims can ask sharper questions, but they cannot trigger trades.</h2>
        <p>
          Qadam keeps live data sources, research resources, private priors, and Fund Manager comments
          separate so every signal can show where it came from and how much trust it deserves.
        </p>
      </section>
    </main>
  );
}
