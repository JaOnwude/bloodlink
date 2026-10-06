/**
 * Loads one resource from the API when a component appears.
 *
 * The request is cancelled if the component goes away or the path changes, and `reload`
 * fetches it again (for example after a change). Pass `null` as the path to hold off, such
 * as while waiting on another resource this one depends on.
 *
 * State is only updated from the request's callbacks, never synchronously in the effect.
 */

import { useCallback, useEffect, useState } from "react";

import { ApiError, api, isAbortError } from "@/lib/api";

interface ResourceState<T> {
  data: T | null;
  error: ApiError | null;
  /** True once a first answer (data or error) has arrived. */
  loaded: boolean;
}

export function useResource<T>(path: string | null) {
  const [state, setState] = useState<ResourceState<T>>({ data: null, error: null, loaded: false });
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (path === null) return;

    const controller = new AbortController();
    api
      .get<T>(path, { signal: controller.signal })
      .then((data) => setState({ data, error: null, loaded: true }))
      .catch((error: unknown) => {
        if (isAbortError(error)) return;
        const failure =
          error instanceof ApiError ? error : new ApiError(0, "Something went wrong.", error);
        setState({ data: null, error: failure, loaded: true });
      });

    return () => controller.abort();
  }, [path, version]);

  const reload = useCallback(() => setVersion((current) => current + 1), []);

  return { ...state, reload };
}
