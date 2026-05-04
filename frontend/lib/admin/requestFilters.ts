export const DEFAULT_REQUEST_LIMIT = "50";

export type RequestFilters = {
  limit: string;
  request_id: string;
  status: string;
  project_id: string;
  api_key_id: string;
  provider: string;
  requested_model: string;
  model: string;
  model_search: string;
  fallback_used: string;
  error_code: string;
  created_from: string;
  created_to: string;
  completed_from: string;
  completed_to: string;
  min_latency_ms: string;
  max_latency_ms: string;
  min_total_tokens: string;
  max_total_tokens: string;
  min_estimated_cost: string;
  max_estimated_cost: string;
  sort_by: string;
  sort_dir: string;
};

export const defaultRequestFilters: RequestFilters = {
  limit: DEFAULT_REQUEST_LIMIT,
  request_id: "",
  status: "",
  project_id: "",
  api_key_id: "",
  provider: "",
  requested_model: "",
  model: "",
  model_search: "",
  fallback_used: "",
  error_code: "",
  created_from: "",
  created_to: "",
  completed_from: "",
  completed_to: "",
  min_latency_ms: "",
  max_latency_ms: "",
  min_total_tokens: "",
  max_total_tokens: "",
  min_estimated_cost: "",
  max_estimated_cost: "",
  sort_by: "created_at",
  sort_dir: "desc",
};

export function activeRequestFiltersSummary(filters: RequestFilters) {
  function clean(value: string) {
    return value.trim();
  }

  function short(value: string, max = 28) {
    const v = clean(value);
    if (!v) return "";
    return v.length <= max ? v : `${v.slice(0, max - 1)}...`;
  }

  function add(label: string, value: string) {
    const v = clean(value);
    if (!v) return;
    parts.push(`${label}=${short(v)}`);
  }

  function addBool(label: string, value: string) {
    const v = clean(value);
    if (!v) return;
    parts.push(`${label}=${v === "true" ? "yes" : v === "false" ? "no" : short(v)}`);
  }

  function addRange(label: string, min: string, max: string, unit?: string) {
    const a = clean(min);
    const b = clean(max);
    if (!a && !b) return;
    const u = unit ?? "";
    if (a && b) parts.push(`${label}=${short(a)}-${short(b)}${u}`);
    else if (a) parts.push(`${label}>=${short(a)}${u}`);
    else parts.push(`${label}<=${short(b)}${u}`);
  }

  const parts: string[] = [];

  add("req", filters.request_id);
  add("st", filters.status);
  add("proj", filters.project_id);
  add("key", filters.api_key_id);
  add("prov", filters.provider);
  add("reqModel", filters.requested_model);
  add("model", filters.model);
  add("search", filters.model_search);
  addBool("fb", filters.fallback_used);
  add("err", filters.error_code);
  add("from", filters.created_from);
  add("to", filters.created_to);
  add("doneFrom", filters.completed_from);
  add("doneTo", filters.completed_to);
  addRange("lat", filters.min_latency_ms, filters.max_latency_ms, "ms");
  addRange("tok", filters.min_total_tokens, filters.max_total_tokens);
  addRange("$", filters.min_estimated_cost, filters.max_estimated_cost);
  if (filters.sort_by !== "created_at" || filters.sort_dir !== "desc") {
    parts.push(`sort=${short(filters.sort_by || "created_at")}.${short(filters.sort_dir || "desc", 6)}`);
  }
  if (filters.limit && filters.limit !== DEFAULT_REQUEST_LIMIT) {
    add("limit", filters.limit);
  }

  return parts.length ? `Active filters: ${parts.join(" | ")}` : "No active filters.";
}

export function asRequestSortBy(
  value: string,
): "created_at" | "completed_at" | "latency_ms" | "total_tokens" | "estimated_cost" {
  return value === "completed_at" ||
    value === "latency_ms" ||
    value === "total_tokens" ||
    value === "estimated_cost"
    ? value
    : "created_at";
}

export function asRequestSortDir(value: string): "asc" | "desc" {
  return value === "asc" ? "asc" : "desc";
}

export function requestFiltersFromSearch(search: string): RequestFilters {
  const params = new URLSearchParams(search);
  return {
    limit: params.get("limit") ?? DEFAULT_REQUEST_LIMIT,
    request_id: params.get("request_id") ?? "",
    status: params.get("status") ?? "",
    project_id: params.get("project_id") ?? "",
    api_key_id: params.get("api_key_id") ?? "",
    provider: params.get("provider") ?? "",
    requested_model: params.get("requested_model") ?? "",
    model: params.get("model") ?? "",
    model_search: params.get("model_search") ?? "",
    fallback_used: params.get("fallback_used") ?? "",
    error_code: params.get("error_code") ?? "",
    created_from: params.get("created_from") ?? "",
    created_to: params.get("created_to") ?? "",
    completed_from: params.get("completed_from") ?? "",
    completed_to: params.get("completed_to") ?? "",
    min_latency_ms: params.get("min_latency_ms") ?? "",
    max_latency_ms: params.get("max_latency_ms") ?? "",
    min_total_tokens: params.get("min_total_tokens") ?? "",
    max_total_tokens: params.get("max_total_tokens") ?? "",
    min_estimated_cost: params.get("min_estimated_cost") ?? "",
    max_estimated_cost: params.get("max_estimated_cost") ?? "",
    sort_by: params.get("sort_by") ?? "created_at",
    sort_dir: params.get("sort_dir") ?? "desc",
  };
}

export function requestFiltersFromLocation(): RequestFilters {
  if (typeof window === "undefined") return defaultRequestFilters;
  return requestFiltersFromSearch(window.location.search);
}

export function requestFiltersToQuery(filters: RequestFilters, offset: number) {
  const params = new URLSearchParams();
  params.set("limit", filters.limit || DEFAULT_REQUEST_LIMIT);
  params.set("offset", String(offset));
  for (const [key, value] of Object.entries(filters)) {
    if (key !== "limit" && value) params.set(key, value);
  }
  return params;
}
