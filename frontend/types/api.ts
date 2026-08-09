export type Overview = {
  total_tickets: number;
  sla_breaches: number;
  sla_compliance: number;
  avg_resolution_hours: number;
  previous_total_tickets: number;
  previous_sla_compliance: number | null;
  previous_avg_resolution_hours: number | null;
  previous_sla_breaches: number;
  data_freshness: string;
};

export type TrendPoint = {
  date: string;
  tickets: number;
  breaches: number;
  avg_resolution_hours: number | null;
};

export type CategoryMetric = {
  category_name: string;
  subcategory: string;
  category: string;
  tickets: number;
  avg_resolution_hours: number;
  median_resolution_hours: number;
  breach_rate: number;
};

export type PriorityMetric = {
  priority: string;
  tickets: number;
};

export type ResolutionPayload = {
  distribution: { bucket: string; tickets: number }[];
  byCategory: CategoryMetric[];
};

export type SlaPayload = {
  overall: {
    tickets: number;
    breached: number;
    compliant: number;
    compliance: number;
    breach_rate: number;
  };
  byCategory: { label: string; compliance: number; breach_rate: number }[];
};

export type RootCauseMetric = {
  root_cause: string;
  tickets: number;
  share: number;
};

export type ShiftMetric = {
  shift: string;
  tickets: number;
  avg_resolution_hours: number;
  sla_compliance: number;
  breach_rate: number;
};

export type AgentMetric = {
  agent_id: number;
  agent_name: string;
  team: string;
  shift: string;
  experience_level: string;
  tickets: number;
  avg_resolution_hours: number;
  sla_compliance: number;
  escalation_rate: number;
};

export type Anomaly = {
  type: "resolution_outlier" | "open_beyond_sla" | "category_spike";
  severity: "info" | "warning" | "critical";
  title: string;
  description: string;
  ticketId: string | null;
  metadata: Record<string, string | number | boolean | null>;
};

export type Summary = {
  ticketsCreated: number;
  slaCompliance: number;
  averageResolutionHours: number;
  topCategory: { category: string; tickets: number } | null;
  topRootCause: { root_cause: string; tickets: number } | null;
  largestTrendChange: { category: string; tickets: number; previous_tickets: number; change_pct: number } | null;
  currentSlaRisks: number;
  recommendedInvestigation: string;
  risks: Anomaly[];
};

export type Insight = {
  type: "positive" | "warning" | "critical" | "info";
  title: string;
  description: string;
};

export type DataQuality = {
  duplicate_records: number;
  missing_root_causes: number;
  invalid_records: number;
  data_freshness: string;
};

export type Ticket = {
  ticket_id: string;
  category: string;
  priority: string;
  status: string;
  agent_name: string;
  shift: string;
  created_at: string;
  first_response_at: string | null;
  resolved_at: string | null;
  resolution_hours: number | "";
  hours_open: number;
  sla_hours: number;
  sla_breached: boolean;
  root_cause: string | null;
  resolution_type: string | null;
  escalation_flag: boolean;
  customer_impact: string;
  description: string;
};

export type TicketPage = {
  rows: Ticket[];
  total: number;
};

export type FilterOptions = {
  categories: string[];
  priorities: string[];
  statuses: string[];
  shifts: string[];
};

