import type {
  AlertRunRequest,
  AlertRunResponse,
  CostSummaryResponse,
  HealthResponse,
  RecommendationsResponse,
} from "./types";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function getApiBaseUrl(): string {
  return (process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/$/, "");
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const message =
      payload && typeof payload === "object" && "error" in payload ? String(payload.error) : `Request failed with ${response.status}`;
    throw new ApiError(message, response.status);
  }

  return payload as T;
}

export async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...init.headers,
    },
  });
  return parseJsonResponse<T>(response);
}

export async function withRetry<T>(operation: () => Promise<T>, retries = 1): Promise<T> {
  try {
    return await operation();
  } catch (error) {
    if (retries <= 0 || error instanceof ApiError) {
      throw error;
    }
    return withRetry(operation, retries - 1);
  }
}

export function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return withRetry(() => requestJson<HealthResponse>("/health", { signal }));
}

export function getCostSummary(months: number, signal?: AbortSignal): Promise<CostSummaryResponse> {
  return withRetry(() => requestJson<CostSummaryResponse>(`/costs/summary?months=${months}`, { signal }));
}

export function getRecommendations(months: number, signal?: AbortSignal): Promise<RecommendationsResponse> {
  return withRetry(() => requestJson<RecommendationsResponse>(`/recommendations?months=${months}`, { signal }));
}

export function runAlerts(request: AlertRunRequest, signal?: AbortSignal): Promise<AlertRunResponse> {
  return requestJson<AlertRunResponse>("/alerts/run", {
    method: "POST",
    body: JSON.stringify(request),
    signal,
  });
}
