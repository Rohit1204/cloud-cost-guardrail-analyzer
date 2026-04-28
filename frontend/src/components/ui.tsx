import { AlertCircle, CheckCircle2, Loader2, RefreshCcw } from "lucide-react";
import type { ReactNode } from "react";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-3xl border border-slate-200 bg-white/90 p-5 shadow-sm shadow-slate-200/80 ${className}`}>{children}</section>;
}

export function SectionHeader({ eyebrow, title, action }: { eyebrow?: string; title: string; action?: ReactNode }) {
  return (
    <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow ? <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-600">{eyebrow}</p> : null}
        <h2 className="mt-1 text-xl font-semibold text-slate-950">{title}</h2>
      </div>
      {action}
    </div>
  );
}

export function Badge({ children, tone = "slate" }: { children: ReactNode; tone?: "red" | "amber" | "blue" | "green" | "slate" }) {
  const tones = {
    red: "border-red-200 bg-red-50 text-red-700",
    amber: "border-amber-200 bg-amber-50 text-amber-700",
    blue: "border-blue-200 bg-blue-50 text-blue-700",
    green: "border-emerald-200 bg-emerald-50 text-emerald-700",
    slate: "border-slate-200 bg-slate-50 text-slate-700",
  };
  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${tones[tone]}`}>{children}</span>;
}

export function LoadingBlock({ label = "Loading data" }: { label?: string }) {
  return (
    <div className="flex min-h-40 items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-slate-50 text-sm text-slate-500">
      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
      {label}
    </div>
  );
}

export function ErrorBlock({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
      <div className="flex items-start gap-2">
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
        <div>
          <p className="font-semibold">Unable to load this section</p>
          <p className="mt-1 text-red-600">{message}</p>
          {onRetry ? (
            <button className="mt-3 inline-flex items-center rounded-xl bg-red-600 px-3 py-2 text-xs font-semibold text-white" onClick={onRetry} type="button">
              <RefreshCcw className="mr-2 h-3.5 w-3.5" />
              Retry
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function EmptyBlock({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
      <CheckCircle2 className="mx-auto h-8 w-8 text-emerald-500" />
      <p className="mt-3 font-semibold text-slate-900">{title}</p>
      <p className="mt-1 text-sm text-slate-500">{detail}</p>
    </div>
  );
}

export function FieldLabel({ children }: { children: ReactNode }) {
  return <label className="text-sm font-medium text-slate-700">{children}</label>;
}
