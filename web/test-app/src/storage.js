const DB_NAME = 'cardenveil-test-v1';
export const events = new EventTarget();
let database;
function db() {
  return database ??= new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => request.result.createObjectStore('session');
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}
export async function read(key) {
  const store = (await db()).transaction('session').objectStore('session');
  return new Promise((resolve, reject) => {
    const req = store.get(key); req.onsuccess = () => resolve(req.result ?? null); req.onerror = () => reject(req.error);
  });
}
export async function write(key, value) {
  const snapshot = JSON.parse(JSON.stringify(value));
  const tx = (await db()).transaction('session', 'readwrite');
  tx.objectStore('session').put(snapshot, key);
  await new Promise((resolve, reject) => { tx.oncomplete = resolve; tx.onerror = () => reject(tx.error); tx.onabort = () => reject(tx.error); });
  events.dispatchEvent(new CustomEvent(key, { detail: snapshot }));
  return snapshot;
}
export async function writeHandle(key, value) {
  const tx = (await db()).transaction('session', 'readwrite');
  tx.objectStore('session').put(value, key);
  await new Promise((resolve, reject) => { tx.oncomplete = resolve; tx.onerror = () => reject(tx.error); tx.onabort = () => reject(tx.error); });
  return value;
}
export function listen(key, handler) {
  const fn = e => handler(e.detail); events.addEventListener(key, fn); return () => events.removeEventListener(key, fn);
}
