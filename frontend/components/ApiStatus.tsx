/**
 * Small diagnostic panel that confirms the browser can reach the API and that the API can
 * reach its database. It exercises the full path (client, CORS, API, PostgreSQL) and is a
 * quick way to diagnose configuration problems in any environment.
 */

import { useEffect, useState } from "react";

import { ApiError, api, isAbortError } from "@/lib/api";
import type { HealthResponse, ReadinessResponse } from "@/types/api";

type StatusState =
  | { phase: "checking" }
  | { phase: "online"; health: HealthResponse; databaseUp: boolean }
  | { phase: "offline"; message: string };

export function ApiStatus() {
  const [state, setState] = useState<StatusState>({ phase: "checking" });

  useEffect(() => {
    // Cancelling on unmount prevents state updates after the component has gone away.
    const controller = new AbortController();

    async function check() {
      try {
        const health = await api.get<HealthResponse>("/health", { signal: controller.signal });

        // Readiness is checked separately: the API can be alive while its database is not.
        let databaseUp = false;
        try {
          await api.get<ReadinessResponse>("/health/ready", { signal: controller.signal });
          databaseUp = true;
        } catch (error) {
          if (isAbortError(error)) return;
        }

        if (!controller.signal.aborted) setState({ phase: "online", health, databaseUp });
      } catch (error) {
        if (isAbortError(error)) return;
        const message =
          error instanceof ApiError ? error.message : "Unexpected error while contacting the API.";
        setState({ phase: "offline", message });
      }
    }

    void check();
    return () => controller.abort();
  }, []);

  if (state.phase === "checking") {
    return <p className="text-sm text-muted-foreground">Checking connection to the API…</p>;
  }

  if (state.phase === "offline") {
    return (
      <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-800">
        API unreachable: {state.message}
      </p>
    );
  }

  return (
    <p className="rounded-md bg-green-50 px-3 py-2 text-sm text-green-800">
      Connected to {state.health.service} v{state.health.version} ({state.health.environment}).
      Database: {state.databaseUp ? "up" : "unavailable"}.
    </p>
  );
}
