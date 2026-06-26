const CACHE_TTL = 5 * 60 * 1000;

interface CacheEntry<T> {
  data: T;
  expiry: number;
}

class ConfigurationCache {
  private store = new Map<string, CacheEntry<unknown>>();

  get<T>(key: string): T | null {
    const entry = this.store.get(key);
    if (!entry) return null;
    if (Date.now() > entry.expiry) {
      this.store.delete(key);
      return null;
    }
    return entry.data as T;
  }

  set<T>(key: string, data: T, ttl = CACHE_TTL): void {
    this.store.set(key, { data, expiry: Date.now() + ttl });
  }

  clear(pattern?: string): void {
    if (!pattern) {
      this.store.clear();
      return;
    }
    const regex = new RegExp(pattern.replace(/\*/g, ".*"));
    for (const key of this.store.keys()) {
      if (regex.test(key)) this.store.delete(key);
    }
  }
}

export const configCache = new ConfigurationCache();
