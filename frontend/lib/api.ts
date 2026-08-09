import type {
  AgentMetric,
  Anomaly,
  CategoryMetric,
  DataQuality,
  FilterOptions,
  Insight,
  Overview,
  PriorityMetric,
  ResolutionPayload,
  RootCauseMetric,
  ShiftMetric,
  SlaPayload,
  Summary,
  TicketPage,
  TrendPoint
} from "@/types/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type DateRange = {
  startDate?: string;
  endDate?: string;
};

export type TicketQuery = DateRange & {
  page?: number;
  pageSize?: number;
  category?: string;
  priority?: string;
  status?: string;
  shift?: string;
  slaStatus?: string;
  search?: string;
  sortBy?: string;
  direction?: "asc" | "desc";
};

export async function apiGet<T>(path: string, params: Record<string, string | number | undefined> = {}): Promise<T> {
  const url = new URL(path, API_URL);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") url.searchParams.set(key, String(value));
  });
  const response = await fetch(url.toString(), { cache: "no-store" });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

function rangeParams(range: DateRange) {
  return {
    start_date: range.startDate,
    end_date: range.endDate
  };
}

export async function fetchDashboard(range: DateRange) {
  const params = rangeParams(range);
  const [
    overview,
    trends,
    categories,
    priorities,
    resolution,
    sla,
    rootCauses,
    agents,
    shifts,
    anomalies,
    summary,
    insights,
    quality
  ] = await Promise.all([
    apiGet<Overview>("/api/overview", params),
    apiGet<TrendPoint[]>("/api/tickets/trend", params),
    apiGet<CategoryMetric[]>("/api/tickets/categories", params),
    apiGet<PriorityMetric[]>("/api/tickets/priorities", params),
    apiGet<ResolutionPayload>("/api/resolution", params),
    apiGet<SlaPayload>("/api/sla", params),
    apiGet<RootCauseMetric[]>("/api/root-causes", params),
    apiGet<AgentMetric[]>("/api/agents", params),
    apiGet<ShiftMetric[]>("/api/shifts", params),
    apiGet<Anomaly[]>("/api/anomalies", params),
    apiGet<Summary>("/api/summary"),
    apiGet<Insight[]>("/api/insights", params),
    apiGet<DataQuality>("/api/data-quality")
  ]);
  return { overview, trends, categories, priorities, resolution, sla, rootCauses, agents, shifts, anomalies, summary, insights, quality };
}

export function fetchTickets(query: TicketQuery) {
  return apiGet<TicketPage>("/api/tickets", {
    start_date: query.startDate,
    end_date: query.endDate,
    page: query.page,
    page_size: query.pageSize,
    category: query.category,
    priority: query.priority,
    status: query.status,
    shift: query.shift,
    sla_status: query.slaStatus,
    search: query.search,
    sort_by: query.sortBy,
    direction: query.direction
  });
}

export function fetchFilterOptions() {
  return apiGet<FilterOptions>("/api/filter-options");
}
