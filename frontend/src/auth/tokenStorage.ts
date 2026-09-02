import type { KeyValueStorageInterface } from 'aws-amplify/utils'

// AC-11: tokens must never survive a tab close, so they are held in a plain
// in-memory Map, overriding Amplify's localStorage default -- not
// sessionStorage or any other persisted browser storage.
const store = new Map<string, string>()

export const inMemoryTokenStorage: KeyValueStorageInterface = {
  async setItem(key: string, value: string) {
    store.set(key, value)
  },
  async getItem(key: string) {
    return store.has(key) ? store.get(key)! : null
  },
  async removeItem(key: string) {
    store.delete(key)
  },
  async clear() {
    store.clear()
  },
}
