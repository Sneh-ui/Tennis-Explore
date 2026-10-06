import { useAuthStore } from '@/store/auth-store'

export function useAuth() {
  const store = useAuthStore()
  return {
    user: store.user,
    token: store.accessToken,
    refreshToken: store.refreshToken,
    loading: store.loading,
    isAuthenticated: store.isAuthenticated(),
    isAdmin: store.isAdmin(),
    isCoach: store.isCoach(),
    hasRole: store.hasRole,
    login: store.login,
    logout: store.logout,
    validateSession: store.validateSession,
    setUser: store.setUser,
  }
}
