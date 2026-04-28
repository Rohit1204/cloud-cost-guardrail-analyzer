"use client";

import { Send } from "lucide-react";
import { useState } from "react";
import { runAlerts } from "@/lib/api";
import type { AlertRunResponse } from "@/lib/types";
import { Badge, Card, ErrorBlock, FieldLabel, SectionHeader } from "./ui";

type Props = {
  months: number;
};

function allowedRecipients(): string[] {
  return (process.env.NEXT_PUBLIC_ALLOWED_ALERT_EMAILS || "")
    .split(",")
    .map((email) => email.trim())
    .filter(Boolean);
}

function statusTone(status: string): "green" | "amber" | "red" | "slate" {
  if (status === "delivered") {
    return "green";
  }
  if (status === "partial_or_failed") {
    return "red";
  }
  if (status.startsWith("skipped")) {
    return "amber";
  }
  return "slate";
}

export function AlertRunner({ months }: Props) {
  const recipientOptions = allowedRecipients();
  const [gmailRecipient, setGmailRecipient] = useState(recipientOptions[0] ?? "");
  const [channels, setChannels] = useState({ gmail: true, whatsapp: false });
  const [result, setResult] = useState<AlertRunResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submitAlertRun() {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const selectedChannels = Object.entries(channels)
        .filter(([, enabled]) => enabled)
        .map(([channel]) => channel);
      const response = await runAlerts({
        cost_months: months,
        alert_channels: selectedChannels,
        gmail_recipient: gmailRecipient.trim() || undefined,
      });
      setResult(response);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to run alerts");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <SectionHeader eyebrow="Notify" title="Run alerts" />
      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <div className="space-y-4">
          {recipientOptions.length > 0 ? (
            <div className="space-y-2">
              <FieldLabel>Allowed Gmail recipient</FieldLabel>
              <select
                aria-label="Allowed Gmail recipient"
                className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none ring-blue-500/20 transition focus:border-blue-500 focus:ring-4"
                onChange={(event) => setGmailRecipient(event.target.value)}
                value={gmailRecipient}
              >
                {recipientOptions.map((email) => (
                  <option key={email} value={email}>
                    {email}
                  </option>
                ))}
              </select>
              <p className="text-xs text-slate-500">Only approved recipients can be selected. The backend enforces the same allowlist.</p>
            </div>
          ) : (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
              Configure `NEXT_PUBLIC_ALLOWED_ALERT_EMAILS` to show approved recipient choices.
            </div>
          )}

          <div className="space-y-2">
            <FieldLabel>Channels</FieldLabel>
            <div className="flex flex-wrap gap-3">
              {(["gmail", "whatsapp"] as const).map((channel) => (
                <label className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-700" key={channel}>
                  <input
                    checked={channels[channel]}
                    className="h-4 w-4 rounded border-slate-300"
                    onChange={(event) => setChannels((current) => ({ ...current, [channel]: event.target.checked }))}
                    type="checkbox"
                  />
                  {channel}
                </label>
              ))}
            </div>
          </div>

          <button
            className="inline-flex w-full items-center justify-center rounded-2xl bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto"
            disabled={loading || (!channels.gmail && !channels.whatsapp) || (channels.gmail && recipientOptions.length === 0)}
            onClick={submitAlertRun}
            type="button"
          >
            <Send className="mr-2 h-4 w-4" />
            {loading ? "Running alerts..." : "Run alert workflow"}
          </button>
        </div>

        <div className="rounded-2xl bg-slate-50 p-4">
          {error ? <ErrorBlock message={error} onRetry={submitAlertRun} /> : null}
          {!error && !result ? <p className="text-sm text-slate-500">Run alerts to send the current recommendations through selected channels.</p> : null}
          {result ? (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={statusTone(result.alert_run.delivery_status)}>{result.alert_run.delivery_status.replace(/_/g, " ")}</Badge>
                <span className="text-sm text-slate-500">{result.alert_run.recommendations_sent_count} recommendations sent</span>
              </div>
              <div className="grid gap-3 text-sm sm:grid-cols-2">
                <p className="rounded-xl bg-white p-3">
                  <span className="block text-slate-500">Findings</span>
                  <span className="font-semibold text-slate-900">{result.finding_count}</span>
                </p>
                <p className="rounded-xl bg-white p-3">
                  <span className="block text-slate-500">Notifications</span>
                  <span className="font-semibold text-slate-900">{result.alert_run.notification_count}</span>
                </p>
              </div>
              <div className="space-y-2">
                {result.notifications.map((notification) => (
                  <p className="rounded-xl bg-white p-3 text-sm text-slate-700" key={`${notification.channel}-${notification.detail}`}>
                    <span className="font-semibold">{notification.channel}:</span> {notification.detail}
                  </p>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </Card>
  );
}
