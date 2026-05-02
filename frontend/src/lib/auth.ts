export type AuthUser = {
  email: string;
  name?: string;
  picture?: string;
};

const TOKEN_KEY = "cloud-cost-google-id-token";
const USER_KEY = "cloud-cost-google-user";
const memoryStorage = new Map<string, string>();

function storageGet(key: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    if (typeof window.localStorage?.getItem === "function") {
      return window.localStorage.getItem(key);
    }
  } catch {
    return memoryStorage.get(key) ?? null;
  }
  return memoryStorage.get(key) ?? null;
}

function storageSet(key: string, value: string) {
  if (typeof window === "undefined") {
    return;
  }
  try {
    if (typeof window.localStorage?.setItem === "function") {
      window.localStorage.setItem(key, value);
      return;
    }
  } catch {
    // Fall back to memory storage when browser storage is blocked.
  }
  memoryStorage.set(key, value);
}

function storageRemove(key: string) {
  if (typeof window === "undefined") {
    return;
  }
  try {
    if (typeof window.localStorage?.removeItem === "function") {
      window.localStorage.removeItem(key);
    }
  } catch {
    // Fall back to memory storage when browser storage is blocked.
  }
  memoryStorage.delete(key);
}

function decodeJwtPayload(token: string): Record<string, unknown> {
  const [, payload] = token.split(".");
  if (!payload) {
    return {};
  }
  try {
    return JSON.parse(window.atob(payload.replace(/-/g, "+").replace(/_/g, "/"))) as Record<string, unknown>;
  } catch {
    return {};
  }
}

export function getGoogleClientId(): string {
  return process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";
}

/** Comma-separated emails; must match server AUTH_ALLOWED_EMAILS. Falls back to NEXT_PUBLIC_ALLOWED_ALERT_EMAILS. */
export function getAuthAllowedEmailSet(): Set<string> {
  const raw = process.env.NEXT_PUBLIC_AUTH_ALLOWED_EMAILS || process.env.NEXT_PUBLIC_ALLOWED_ALERT_EMAILS || "";
  const emails = raw
    .split(",")
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
  return new Set(emails);
}

export function parseGoogleCredential(token: string): AuthUser {
  const payload = decodeJwtPayload(token);
  return {
    email: String(payload.email ?? ""),
    name: payload.name ? String(payload.name) : undefined,
    picture: payload.picture ? String(payload.picture) : undefined,
  };
}

export type AuthBootstrap = {
  user: AuthUser | null;
  gateError: string | null;
};

/** On load: drop invalid stored sessions when Google sign-in is enabled (aligned with server allowlist). */
export function bootstrapGoogleAuthSession(): AuthBootstrap {
  const clientId = getGoogleClientId();
  const stored = getStoredUser();
  if (!stored?.email) {
    return { user: null, gateError: null };
  }
  if (!clientId) {
    return { user: stored, gateError: null };
  }

  const allowed = getAuthAllowedEmailSet();
  if (allowed.size === 0) {
    clearAuthSession();
    return {
      user: null,
      gateError: "Sign-in is not configured.",
    };
  }

  const normalized = stored.email.trim().toLowerCase();
  if (!allowed.has(normalized)) {
    clearAuthSession();
    return {
      user: null,
      gateError: "This email is not authorized to sign in.",
    };
  }

  return { user: stored, gateError: null };
}

export function getAuthToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return storageGet(TOKEN_KEY);
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") {
    return null;
  }
  const rawUser = storageGet(USER_KEY);
  if (!rawUser) {
    return null;
  }
  try {
    return JSON.parse(rawUser) as AuthUser;
  } catch {
    return null;
  }
}

export function storeAuthSession(token: string, user: AuthUser) {
  storageSet(TOKEN_KEY, token);
  storageSet(USER_KEY, JSON.stringify(user));
}

export function storeGoogleCredential(token: string): AuthUser {
  const user = parseGoogleCredential(token);
  storeAuthSession(token, user);
  return user;
}

export function clearAuthSession() {
  storageRemove(TOKEN_KEY);
  storageRemove(USER_KEY);
}
