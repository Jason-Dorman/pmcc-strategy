// A page-level warning (UI-SPEC §2, §8): synthetic data, a schema mismatch, a Reg T breach.
import type { ReactNode } from "react";

export function WarningBanner({ children }: { children: ReactNode }) {
  return (
    <div className="pm-warn" role="alert">
      {children}
    </div>
  );
}
