import { useEffect, useState } from "react";

export default function useDebounced<T>(value: T, debounceMs: number): T {
  const [debounced, setDebounced] = useState<T>(value);

  useEffect(() => {
    const timeout = setTimeout(() => {
      setDebounced(value);
    }, debounceMs)

    return () => clearTimeout(timeout);
  }, [value, debounceMs])

  return debounced;
}
