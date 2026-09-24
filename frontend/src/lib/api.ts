import type { CurrentUser } from "../types/auth";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

interface ErrorBody {
  detail?: string;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

async function parseError(response: Response): Promise<ApiError> {
  let detail = `http_${response.status}`;

  try {
    const body = (await response.json()) as ErrorBody;
    if (typeof body.detail === "string") {
      detail = body.detail;
    }
  } catch {
    // The status code remains available even when the response has no JSON body.
  }

  return new ApiError(response.status, detail);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      Accept: "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as T;
}

async function getCsrfToken(): Promise<string> {
  const response = await request<{ csrf_token: string }>("/api/auth/csrf");
  return response.csrf_token;
}

export async function createSession(idToken: string): Promise<CurrentUser> {
  const csrfToken = await getCsrfToken();

  return request<CurrentUser>("/api/auth/session", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken,
    },
    body: JSON.stringify({ id_token: idToken }),
  });
}

export function getCurrentUser(): Promise<CurrentUser> {
  return request<CurrentUser>("/api/auth/me");
}

export async function destroySession(): Promise<void> {
  const csrfToken = await getCsrfToken();
  await request<{ status: string }>("/api/auth/logout", {
    method: "POST",
    headers: {
      "X-CSRF-Token": csrfToken,
    },
  });
}
