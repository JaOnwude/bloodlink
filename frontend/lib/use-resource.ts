/**
 * Loads one resource from the API when a component appears.
 *
 * The request is cancelled if the component goes away or the path changes, and `reload`
 * fetches it again (for example after a change). Pass `null` as the path to hold off, such
 * as while waiting on another resource this one depends on.
 *
 * Data and errors are reported only when they belong to the path currently asked for. When
 * the path changes (a different page, a different filter), `loaded` becomes false until the
 * new answer arrives, so a screen never shows the previous answer as if it were the new one.
 * A reload of the same path keeps showing the current data while it refreshes.
 *
 * State is only updated from the request's callbacks, never synchronously in the effect.
 */

import { useCallback, useEffect, useState } from "react";

import { ApiError, api, isAbortError } from "@/lib/api";

interface ResourceState<T> {
  data: T | null;
  error: ApiError | null;
  /** The path this answer belongs to. */
  path: string | null;
}

export function useResource<T>(path: string | null) {
  const [state, setState] = useState<ResourceState<T>>({ data: null, error: null, path: null });
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (path === null) return;

    const controller = new AbortController();
    api
      .get<T>(path, { signal: controller.signal })
      .then((data) => setState({ data, error: null, path }))
      .catch((error: unknown) => {
        if (isAbortError(error)) return;
        const failure =
          error instanceof ApiError ? error : new ApiError(0, "Something went wrong.", error);
        setState({ data: null, error: failure, path });
      });

    return () => controller.abort();
  }, [path, version]);

  const reload = useCallback(() => setVersion((current) => current + 1), []);

  // True once an answer has arrived for the path being asked for.
  const loaded = path !== null && state.path === path;

  return {
    data: loaded ? state.data : null,
    error: loaded ? state.error : null,
    loaded,
    reload,
  };
}
