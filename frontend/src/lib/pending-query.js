import { encryptText, decryptText } from './crypto'

const PENDING_QUERY_KEY = 'tennis-explore.pending-query'

export const hasPendingQuery = () => Boolean(localStorage.getItem(PENDING_QUERY_KEY))

export const savePendingQuery = async (query) => {
  localStorage.setItem(PENDING_QUERY_KEY, await encryptText(query))
}

export const consumePendingQuery = async () => {
  const raw = localStorage.getItem(PENDING_QUERY_KEY)
  if (!raw) return null
  localStorage.removeItem(PENDING_QUERY_KEY)
  try {
    return await decryptText(raw)
  } catch {
    return null
  }
}
