let pendingKey: string | null = null;

export function setPlaygroundApiKeyOnce(key: string): void {
  if (key.trim()) pendingKey = key;
}

export function takePlaygroundApiKeyOnce(): string | null {
  const key = pendingKey;
  pendingKey = null;
  return key;
}
