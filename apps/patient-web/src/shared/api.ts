const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

// Carries the HTTP status and, when the API sent one, the structured
// {"reason": "..."} detail body — lets callers like the consent-form screen
// render a distinct message per failure mode (expired vs invalidated vs
// completed) instead of one generic error string.
export class ApiError extends Error {
  status: number;
  reason: string | undefined;

  constructor(path: string, status: number, body: unknown) {
    super(`Request to ${path} failed (${status}): ${JSON.stringify(body)}`);
    this.status = status;
    this.reason =
      typeof body === 'object' &&
      body !== null &&
      'detail' in body &&
      typeof body.detail === 'object' &&
      body.detail !== null &&
      'reason' in body.detail &&
      typeof body.detail.reason === 'string'
        ? body.detail.reason
        : undefined;
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => undefined);
    throw new ApiError(path, response.status, body);
  }
  return response.json() as Promise<T>;
}
