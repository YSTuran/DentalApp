import type { CurrentUser } from "../types/auth";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

interface ErrorBody {
  detail?: unknown;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
    public readonly data: unknown = null,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

type SessionInvalidationListener = (error: ApiError) => void;

const sessionInvalidationListeners = new Set<SessionInvalidationListener>();

export function subscribeToSessionInvalidation(
  listener: SessionInvalidationListener,
): () => void {
  sessionInvalidationListeners.add(listener);
  return () => {
    sessionInvalidationListeners.delete(listener);
  };
}

function invalidatesSession(error: ApiError): boolean {
  return error.status === 401
    || (
      error.status === 403
      && ["account_not_provisioned", "account_inactive"].includes(error.detail)
    );
}

function reportApiError(error: ApiError): ApiError {
  if (invalidatesSession(error)) {
    csrfToken = null;
    for (const listener of sessionInvalidationListeners) listener(error);
  }
  return error;
}

async function parseError(response: Response): Promise<ApiError> {
  let detail = `http_${response.status}`;
  let data: unknown = null;

  try {
    const body = (await response.json()) as ErrorBody;
    if (typeof body.detail === "string") {
      detail = body.detail;
    } else if (body.detail !== undefined) {
      data = body.detail;
      if (
        typeof body.detail === "object"
        && body.detail !== null
        && "code" in body.detail
        && typeof body.detail.code === "string"
      ) {
        detail = body.detail.code;
      } else if (Array.isArray(body.detail)) {
        detail = "validation_error";
      }
    }
  } catch {
    // The status code remains available even when the response has no JSON body.
  }

  return new ApiError(response.status, detail, data);
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      Accept: "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    throw reportApiError(await parseError(response));
  }

  return (await response.json()) as T;
}

export async function apiBlobRequest(path: string, init?: RequestInit): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      Accept: "application/octet-stream",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    throw reportApiError(await parseError(response));
  }

  return response.blob();
}

export async function apiArrayBufferRequest(
  path: string,
  init?: RequestInit,
): Promise<ArrayBuffer> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      Accept: "application/octet-stream",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    throw reportApiError(await parseError(response));
  }

  return response.arrayBuffer();
}

let csrfToken: string | null = null;
let csrfTokenRequest: Promise<string> | null = null;

async function getCsrfToken(signal?: AbortSignal | null): Promise<string> {
  if (csrfToken !== null) return csrfToken;
  if (csrfTokenRequest !== null) return csrfTokenRequest;

  csrfTokenRequest = apiRequest<{ csrf_token: string }>("/api/auth/csrf", { signal })
    .then((response) => {
      csrfToken = response.csrf_token;
      return response.csrf_token;
    })
    .finally(() => {
      csrfTokenRequest = null;
    });
  return csrfTokenRequest;
}

export async function csrfRequest<T>(path: string, init: RequestInit): Promise<T> {
  async function send(token: string): Promise<T> {
    return apiRequest<T>(path, {
      ...init,
      headers: {
        "X-CSRF-Token": token,
        ...init.headers,
      },
    });
  }

  const token = await getCsrfToken(init.signal);
  try {
    return await send(token);
  } catch (error) {
    if (!(error instanceof ApiError) || error.detail !== "csrf_validation_failed") {
      throw error;
    }
    csrfToken = null;
    return send(await getCsrfToken(init.signal));
  }
}

export async function createSession(
  idToken: string,
  rememberMe: boolean,
): Promise<CurrentUser> {
  return csrfRequest<CurrentUser>("/api/auth/session", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ id_token: idToken, remember_me: rememberMe }),
  });
}

export function getCurrentUser(): Promise<CurrentUser> {
  return apiRequest<CurrentUser>("/api/auth/me");
}

export async function destroySession(): Promise<void> {
  await csrfRequest<{ status: string }>("/api/auth/logout", {
    method: "POST",
  });
}

export function recordPasswordChanged(
  idToken: string,
  rememberMe: boolean,
): Promise<CurrentUser> {
  return csrfRequest<CurrentUser>("/api/auth/password-changed", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ id_token: idToken, remember_me: rememberMe }),
  });
}
