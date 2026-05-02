"use client";

import { BarChart3, Bell, Loader2, Lock, ShieldCheck } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  bootstrapGoogleAuthSession,
  clearAuthSession,
  getAuthAllowedEmailSet,
  getGoogleClientId,
  parseGoogleCredential,
  storeAuthSession,
  type AuthUser,
} from "@/lib/auth";
import { Dashboard } from "./Dashboard";
import { Card } from "./ui";

type GoogleCredentialResponse = {
  credential?: string;
};

type GoogleAccounts = {
  accounts: {
    id: {
      initialize: (config: { client_id: string; callback: (response: GoogleCredentialResponse) => void }) => void;
      renderButton: (element: HTMLElement, options: Record<string, string | number | boolean>) => void;
    };
  };
};

declare global {
  interface Window {
    google?: GoogleAccounts;
  }
}

const SCRIPT_ID = "google-identity-services";

function loadGoogleScript(onLoad: () => void) {
  if (window.google) {
    onLoad();
    return;
  }
  const existing = document.getElementById(SCRIPT_ID) as HTMLScriptElement | null;
  if (existing) {
    existing.addEventListener("load", onLoad, { once: true });
    return;
  }
  const script = document.createElement("script");
  script.id = SCRIPT_ID;
  script.src = "https://accounts.google.com/gsi/client";
  script.async = true;
  script.defer = true;
  script.addEventListener("load", onLoad, { once: true });
  document.head.appendChild(script);
}

const featureItems = [
  {
    icon: BarChart3,
    title: "Costs & trends",
    detail: "MTD spend, charts, and drivers in one place.",
  },
  {
    icon: Lock,
    title: "Protected access",
    detail: "Google-verified sign-in and allowed-email checks.",
  },
  {
    icon: Bell,
    title: "Alerts & workflow",
    detail: "Run notifications and track recommendation status.",
  },
] as const;

export function LoginGate() {
  const googleButtonRef = useRef<HTMLDivElement>(null);
  const boot = useMemo(() => bootstrapGoogleAuthSession(), []);
  const [user, setUser] = useState<AuthUser | null>(boot.user);
  const [gateError, setGateError] = useState<string | null>(boot.gateError);
  const [error, setError] = useState<string | null>(null);
  const [gsiReady, setGsiReady] = useState(false);
  const clientId = getGoogleClientId();
  const displayError = error ?? gateError;

  useEffect(() => {
    if (!clientId || user) {
      return;
    }

    loadGoogleScript(() => {
      if (!window.google || !googleButtonRef.current) {
        setError("Google sign-in script did not load.");
        return;
      }
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: (response) => {
          if (!response.credential) {
            setError("Google did not return a sign-in credential.");
            return;
          }
          const parsed = parseGoogleCredential(response.credential);
          if (!parsed.email?.trim()) {
            setError("Google did not return an email on this account.");
            return;
          }

          const allowed = getAuthAllowedEmailSet();
          if (allowed.size === 0) {
            setGateError(null);
            setError("Sign-in is not configured.");
            return;
          }

          const normalized = parsed.email.trim().toLowerCase();
          if (!allowed.has(normalized)) {
            setGateError(null);
            setError("This email is not authorized to sign in.");
            return;
          }

          setError(null);
          setGateError(null);
          storeAuthSession(response.credential, parsed);
          setUser(parsed);
        },
      });
      window.google.accounts.id.renderButton(googleButtonRef.current, {
        theme: "outline",
        size: "large",
        width: 320,
        text: "signin_with",
      });
      setGsiReady(true);
    });
  }, [clientId, user]);

  function signOut() {
    clearAuthSession();
    setUser(null);
    setGateError(null);
    setError(null);
  }

  if (user) {
    return <Dashboard onSignOut={signOut} user={user} />;
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-slate-50 px-4 py-12">
      <div
        aria-hidden
        className="login-page-blob pointer-events-none absolute -left-32 top-0 h-72 w-72 rounded-full bg-blue-400/25 blur-3xl"
        style={{ animation: "login-blob 18s ease-in-out infinite" }}
      />
      <div
        aria-hidden
        className="login-page-blob pointer-events-none absolute -right-24 bottom-0 h-80 w-80 rounded-full bg-cyan-400/20 blur-3xl"
        style={{ animation: "login-blob 22s ease-in-out infinite reverse" }}
      />
      <div
        aria-hidden
        className="login-page-blob pointer-events-none absolute left-1/2 top-1/3 h-64 w-64 -translate-x-1/2 rounded-full bg-indigo-400/15 blur-3xl"
        style={{ animation: "login-blob 26s ease-in-out infinite" }}
      />

      <Card className="login-stagger group relative z-10 max-w-lg border-slate-200/90 bg-white/85 p-6 shadow-lg shadow-slate-300/40 backdrop-blur-md transition duration-300 hover:border-blue-200/80 hover:shadow-xl hover:shadow-blue-500/10 sm:p-8">
        <div className="login-shield-ring mb-6 inline-flex rounded-2xl bg-gradient-to-br from-blue-50 to-cyan-50 p-3.5 text-blue-700 ring-1 ring-blue-100/80 transition duration-300 group-hover:scale-[1.03] group-hover:ring-blue-200/80" style={{ animation: "login-shield-pulse 3s ease-in-out infinite" }}>
          <ShieldCheck className="h-7 w-7" aria-hidden />
        </div>

        <div style={{ animation: "login-fade-up 0.55s ease-out 0.05s both" }}>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-blue-600">Cloud Cost Guardrail</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">Welcome back</h1>
          <p className="mt-3 text-sm leading-relaxed text-slate-600">
            Sign in with Google to open your dashboard—cost insights, recommendations, and alert controls stay behind verified access.
          </p>
        </div>

        <ul className="mt-7 grid gap-3 sm:grid-cols-3">
          {featureItems.map((item, i) => {
            const Icon = item.icon;
            return (
              <li
                key={item.title}
                className="rounded-2xl border border-slate-100 bg-slate-50/80 px-3 py-3 text-center transition duration-200 hover:-translate-y-0.5 hover:border-blue-200/60 hover:bg-white hover:shadow-md hover:shadow-slate-200/80"
                style={{ animation: `login-fade-up 0.5s ease-out ${0.12 + i * 0.06}s both` }}
              >
                <div className="mx-auto mb-2 flex h-9 w-9 items-center justify-center rounded-xl bg-white text-blue-600 shadow-sm ring-1 ring-slate-100 transition group-hover:ring-blue-100">
                  <Icon className="h-4 w-4" aria-hidden />
                </div>
                <p className="text-xs font-semibold text-slate-900">{item.title}</p>
                <p className="mt-1 text-[11px] leading-snug text-slate-500">{item.detail}</p>
              </li>
            );
          })}
        </ul>

        <div className="mt-8">
          {clientId ? (
            <div className="relative flex min-h-[52px] w-full flex-col items-center justify-center">
              {!gsiReady ? (
                <div
                  className="absolute inset-0 z-10 flex items-center justify-center gap-2 rounded-2xl border border-dashed border-slate-200 bg-slate-50/95 backdrop-blur-[2px]"
                  aria-live="polite"
                >
                  <Loader2 className="h-4 w-4 shrink-0 animate-spin text-blue-600" aria-hidden />
                  <span className="text-sm text-slate-600">Preparing sign-in…</span>
                </div>
              ) : null}
              <div
                ref={googleButtonRef}
                className={`flex min-h-[44px] w-full justify-center transition-opacity duration-300 ${gsiReady ? "opacity-100" : "opacity-0"}`}
              />
            </div>
          ) : (
            <button
              className="relative w-full overflow-hidden rounded-2xl bg-gradient-to-r from-slate-900 to-slate-800 px-5 py-3.5 text-sm font-semibold text-white shadow-md shadow-slate-900/20 transition hover:from-slate-800 hover:to-slate-700 hover:shadow-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500 active:scale-[0.99]"
              onClick={() => setUser({ email: "local-dev@example.com", name: "Local development" })}
              type="button"
            >
              Continue in local development
            </button>
          )}
        </div>

        {displayError ? (
          <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 p-4 transition-opacity duration-200" role="alert">
            <p className="text-sm font-medium text-red-900">{displayError}</p>
          </div>
        ) : null}

        {!clientId ? (
          <p className="mt-5 rounded-xl bg-slate-50 px-3 py-2 text-xs leading-relaxed text-slate-500">
            <span className="font-medium text-slate-600">Developer tip:</span> set{" "}
            <code className="rounded bg-slate-200/80 px-1.5 py-0.5 font-mono text-[11px] text-slate-800">NEXT_PUBLIC_GOOGLE_CLIENT_ID</code> for the
            real Google button.
          </p>
        ) : (
          <p className="mt-5 text-center text-xs text-slate-400">By continuing, Google shares your name and email with this app for access control.</p>
        )}
      </Card>
    </main>
  );
}
