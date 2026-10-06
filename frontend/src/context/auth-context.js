import { createContext } from 'react'

export const DEMO_ACCOUNT = {
  name: 'Admin',
  email: 'admin@tennisexplore.au',
  password: 'admin123',
  role: 'admin',
}

export const TOKEN_KEY = 'tennis-explore.token'
export const SESSION_KEY = 'tennis-explore.session'

export const readJSON = (key) => {
  try {
    return JSON.parse(localStorage.getItem(key))
  } catch {
    return null
  }
}

export const getStoredToken = () => localStorage.getItem(TOKEN_KEY)

export const AuthContext = createContext(null)
