import { useState, useEffect } from 'react'
import { AuthContext, SESSION_KEY, TOKEN_KEY, readJSON } from './auth-context'
import { loginRequest, fetchMe } from '@/lib/api'

const toSession = ({ name, email, role, id, profile_pic }) => ({ id, name, email, role, profile_pic })

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => readJSON(SESSION_KEY))
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY))
  const [loading, setLoading] = useState(() => Boolean(localStorage.getItem(TOKEN_KEY)))

  const persistSession = (userData, accessToken) => {
    const session = toSession(userData)
    localStorage.setItem(SESSION_KEY, JSON.stringify(session))
    localStorage.setItem(TOKEN_KEY, accessToken)
    setUser(session)
    setToken(accessToken)
  }

  const logout = () => {
    localStorage.removeItem(SESSION_KEY)
    localStorage.removeItem(TOKEN_KEY)
    setUser(null)
    setToken(null)
    setLoading(false)
  }

  // Validate token on mount / refresh — ensures header is dynamic and token is still valid
  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_KEY)
    if (!storedToken) {
      setLoading(false)
      return
    }
    // token exists -> validate with backend
    fetchMe(storedToken)
      .then((freshUser) => {
        const session = toSession(freshUser)
        localStorage.setItem(SESSION_KEY, JSON.stringify(session))
        setUser(session)
        // keep token as is
      })
      .catch(() => {
        // invalid / expired -> clear session
        localStorage.removeItem(SESSION_KEY)
        localStorage.removeItem(TOKEN_KEY)
        setUser(null)
        setToken(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const login = async (credentials) => {
    const data = await loginRequest(credentials)
    persistSession(data.user, data.access_token)
    return data.user
  }

  // signup disabled — no register API
  const signup = async () => {
    throw new Error('Registration is disabled')
  }

  return <AuthContext.Provider value={{ user, token, loading, login, signup, logout }}>{children}</AuthContext.Provider>
}
