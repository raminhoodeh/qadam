export type ModuleStatus = {
  key: string;
  label: string;
  owner: string;
  status: string;
};

export type AdapterStatus = {
  key: string;
  source: string;
  mode: string;
  auth: string;
  trust_score: number;
  default_feed_count?: number;
  default_series_count?: number;
  raw_archive_exists: boolean;
  live_boundary: string;
};

export type ExecutionVenue = {
  key: string;
  name: string;
  adapter: string;
  mode: string;
  first_release_allowed: boolean;
  account_scope: string;
  credential_status: string;
  read_health: string;
  write_health: string;
  kill_switch_status: string;
  notes: string;
};

export type CockpitHealth = {
  ok: boolean;
  status: string;
  source?: string;
  mode: string;
  trial_balance_gbp: number;
  source_count: number;
  expected_source_count: number;
  pipeline_counts: Record<string, number>;
  unresolved_sources: string[];
  modules: ModuleStatus[];
  adapters: Record<string, AdapterStatus>;
  fund_managers: {
    allowlist_emails: string[];
    pending_names: string[];
    login_surface: string;
  };
  resource_registry: {
    status: string;
    resource_count: number;
    boundary: string;
  };
  world_model: {
    status: string;
    corpus_file_count: number;
    claim_count: number;
    evidence_boundary: string;
  };
  governance_forum: {
    status: string;
    comment_count: number;
    visibility: string;
  };
  ingestion_spine: {
    status: string;
    mode: string;
    source_count: number;
    boundary: string;
  };
  source_heartbeat: {
    status: string;
    data_environment_map_path: string;
    generated_at?: string;
    summary?: {
      source_count?: number;
      promoted_adapter_count?: number;
      deferred_count?: number;
      missing_credential_source_count?: number;
      by_runtime_status?: Record<string, number>;
    };
    boundary: string;
  };
  local_stores: {
    status: string;
    summary?: {
      offline_services?: string[];
      reachable_services?: number;
    };
  };
  event_log: {
    status: string;
    backend?: string;
    total_events?: number;
  };
  execution_venues: ExecutionVenue[];
  execution_summary: {
    total: number;
    write_enabled: number;
    first_release_allowed: number;
    live_blocked: string[];
  };
};

const fallbackModules: ModuleStatus[] = [
  { key: "coo", label: "COO", owner: "Python Orchestrator", status: "not_running" },
  { key: "event_log", label: "Event Log", owner: "Local JSONL fallback", status: "fallback" },
  { key: "knowledge_graph", label: "Knowledge Graph", owner: "Embedded Chroma", status: "registered" },
  { key: "execution_registry", label: "Execution Registry", owner: "Risk Agent", status: "disabled" },
  { key: "cockpit", label: "Cockpit", owner: "qadam.trade", status: "registered" }
];

const fallbackHealth: CockpitHealth = {
  ok: false,
  status: "degraded",
  source: "cockpit_fallback",
  mode: "paper",
  trial_balance_gbp: 1000,
  source_count: 35,
  expected_source_count: 35,
  pipeline_counts: { conflict: 5, physical: 7, macro: 6, market: 9, social: 8 },
  unresolved_sources: [],
  modules: fallbackModules,
  adapters: {},
  fund_managers: {
    allowlist_emails: ["raminhoodeh@gmail.com", "troycookecareer@gmail.com", "isioras@yahoo.co.uk"],
    pending_names: ["Akber", "Anas"],
    login_surface: "qadam.trade"
  },
  resource_registry: {
    status: "unknown",
    resource_count: 28,
    boundary: "Resources guide architecture, research, and UX; they are not live data feeds."
  },
  world_model: {
    status: "unknown",
    corpus_file_count: 4,
    claim_count: 5,
    evidence_boundary: "World-model claims are private priors, not factual evidence or trade triggers."
  },
  governance_forum: {
    status: "unknown",
    comment_count: 0,
    visibility: "founding_fund_managers"
  },
  ingestion_spine: {
    status: "unknown",
    mode: "test_data",
    source_count: 35,
    boundary: "No live API calls from fallback mode."
  },
  source_heartbeat: {
    status: "not_started",
    data_environment_map_path: "data/runtime/data_environment_map.json",
    summary: {
      source_count: 35,
      promoted_adapter_count: 0,
      deferred_count: 0,
      missing_credential_source_count: 0
    },
    boundary: "Run source heartbeat locally to build the data environment map."
  },
  local_stores: {
    status: "degraded",
    summary: { offline_services: ["orchestrator"] }
  },
  event_log: {
    status: "not_started",
    backend: "local_jsonl"
  },
  execution_venues: [],
  execution_summary: {
    total: 0,
    write_enabled: 0,
    first_release_allowed: 0,
    live_blocked: []
  }
};

export async function getCockpitHealth(): Promise<CockpitHealth> {
  const orchestratorUrl =
    process.env.QADAM_ORCHESTRATOR_URL ?? process.env.NEXT_PUBLIC_QADAM_ORCHESTRATOR_URL;

  if (!orchestratorUrl) {
    return fallbackHealth;
  }

  try {
    const response = await fetch(orchestratorUrl, {
      cache: "no-store",
      signal: AbortSignal.timeout(900)
    });
    if (!response.ok) {
      return fallbackHealth;
    }
    const health = (await response.json()) as Partial<CockpitHealth>;
    return {
      ...fallbackHealth,
      ...health,
      source: "orchestrator",
      modules: health.modules ?? fallbackHealth.modules,
      adapters: health.adapters ?? fallbackHealth.adapters,
      pipeline_counts: health.pipeline_counts ?? fallbackHealth.pipeline_counts,
      fund_managers: health.fund_managers ?? fallbackHealth.fund_managers,
      source_heartbeat: health.source_heartbeat ?? fallbackHealth.source_heartbeat,
      execution_venues: health.execution_venues ?? fallbackHealth.execution_venues,
      execution_summary: health.execution_summary ?? fallbackHealth.execution_summary
    };
  } catch {
    return fallbackHealth;
  }
}
