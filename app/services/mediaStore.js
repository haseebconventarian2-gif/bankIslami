import crypto from 'crypto';

const store = new Map();
const TTL_MS = 5 * 60 * 1000;

export function saveAudio(buffer, contentType) {
  const id = crypto.randomBytes(16).toString('hex');
  store.set(id, { buffer, contentType, expiresAt: Date.now() + TTL_MS });

  setTimeout(() => store.delete(id), TTL_MS).unref?.();
  return id;
}

export function getAudio(id) {
  const entry = store.get(id);
  if (!entry) return null;
  if (Date.now() > entry.expiresAt) {
    store.delete(id);
    return null;
  }
  return entry;
}
