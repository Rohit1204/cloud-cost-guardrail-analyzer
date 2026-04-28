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
  const payload = decodeJwtPayload(token);
  const user = {
    email: String(payload.email ?? ""),
    name: payload.name ? String(payload.name) : undefined,
    picture: payload.picture ? String(payload.picture) : undefined,
  };
  storeAuthSession(token, user);
  return user;
}

export function clearAuthSession() {
  storageRemove(TOKEN_KEY);
  storageRemove(USER_KEY);
}
