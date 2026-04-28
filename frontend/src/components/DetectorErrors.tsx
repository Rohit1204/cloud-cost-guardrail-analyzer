import type { DetectorError } from "@/lib/types";
import { Badge } from "./ui";

export function DetectorErrors({ errors }: { errors: DetectorError[] }) {
  if (errors.length === 0) {
    return null;
  }

  return (
    <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="amber">Partial data</Badge>
        <p className="text-sm font-medium text-amber-900">Some AWS checks returned errors.</p>
      </div>
      <div className="mt-3 space-y-2">
        {errors.map((error) => (
          <p className="text-sm text-amber-800" key={`${error.detector}-${error.error_type}`}>
            <span className="font-semibold">{error.detector}</span>: {error.message}
          </p>
        ))}
      </div>
    </div>
  );
}
