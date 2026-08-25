import { useState } from 'react'
import { AuthContext, authenticate, registerAccount, readJSON } from './auth-context'

const SESSION_KEY = 'tennis-explore.session'

const toSession = ({ name, email, role }) => ({ name, email, role })

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => readJSON(SESSION_KEY))

  const persistSession = (session) => {
    localStorage.setItem(SESSION_KEY, JSON.stringify(session))
    setUser(session)
  }

  const login = async (credentials) => {
    const account = await authenticate(credentials)
    persistSession(toSession(account))
    return account
  }

  const signup = async (details) => {
    const account = await registerAccount(details)
    persistSession(toSession(account))
    return account
  }

  const logout = () => {
    localStorage.removeItem(SESSION_KEY)
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, login, signup, logout }}>{children}</AuthContext.Provider>
}
