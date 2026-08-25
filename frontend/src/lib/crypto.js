const SECRET = 'tennis-explore-local-encryption-key'

const toBase64 = (bytes) => btoa(String.fromCharCode(...bytes))
const fromBase64 = (str) => Uint8Array.from(atob(str), (c) => c.charCodeAt(0))

const deriveKey = async (salt) => {
  const keyMaterial = await crypto.subtle.importKey('raw', new TextEncoder().encode(SECRET), 'PBKDF2', false, ['deriveKey'])
  return crypto.subtle.deriveKey(
    { name: 'PBKDF2', salt, iterations: 100000, hash: 'SHA-256' },
    keyMaterial,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt']
  )
}

export const encryptText = async (plain) => {
  const salt = crypto.getRandomValues(new Uint8Array(16))
  const iv = crypto.getRandomValues(new Uint8Array(12))
  const key = await deriveKey(salt)
  const data = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, new TextEncoder().encode(plain))
  return JSON.stringify({ v: 1, salt: toBase64(salt), iv: toBase64(iv), data: toBase64(new Uint8Array(data)) })
}

export const decryptText = async (payload) => {
  const { salt, iv, data } = JSON.parse(payload)
  const key = await deriveKey(fromBase64(salt))
  const plain = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: fromBase64(iv) }, key, fromBase64(data))
  return new TextDecoder().decode(plain)
}
