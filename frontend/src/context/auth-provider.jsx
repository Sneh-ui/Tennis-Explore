import { useEffect } from 'react'
import { AuthContext } from './auth-context'
import { useAuthStore } from '@/store/auth-store'

export function AuthProvider({ children }) {
  const validateSession = useAuthStore((s) => s.validateSession)
  const user = useAuthStore((s) => s.user)
  const token = useAuthStore((s) => s.accessToken)
  const refreshToken = useAuthStore((s) => s.refreshToken)
  const loading = useAuthStore((s) => s.loading)
  const login = useAuthStore((s) => s.login)
  const logout = useAuthStore((s) => s.logout)

  useEffect(() => {
    validateSession()
    // migrate old localStorage keys if present (tennis-explore.session/token)
    const oldSession = localStorage.getItem('tennis-explore.session')
    const oldToken = localStorage.getItem('tennis-explore.token')
    if (oldSession || oldToken) {
      localStorage.removeItem('tennis-explore.session')
      localStorage.removeItem('tennis-explore.token')
    }
  }, [validateSession])

  const signup = async () => {
    throw new Error('Registration is disabled')
  }

  // Keep context for backward compat, but also zustand is source of truth
  const value = { user, token, refreshToken, loading, login, signup, logout, isAdmin: user?.role?.toLowerCase() === 'admin' }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
