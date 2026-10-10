/**
 * Injected persistence seam: records and prefs never touch window.localStorage
 * directly — main.tsx builds the real adapter (web), tests build memory.
 */
export interface Storage {
  get(key: string): string | null;
  set(key: string, value: string): void;
  remove(key: string): void;
}

export interface WebStorageArea {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

export function createWebStorage(area: WebStorageArea): Storage {
  return {
    get: (key) => area.getItem(key),
    set: (key, value) => area.setItem(key, value),
    remove: (key) => area.removeItem(key),
  };
}

export function createMemoryStorage(seed: Record<string, string> = {}): Storage {
  const data = new Map(Object.entries(seed));
  return {
    get: (key) => (data.has(key) ? data.get(key)! : null),
    set: (key, value) => void data.set(key, value),
    remove: (key) => void data.delete(key),
  };
}
