import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      loading: false,

      setAuth: ({ user, accessToken, refreshToken }) =>
        set({ user, accessToken, refreshToken, loading: false }),

      setUser: (user) => set({ user }),

      setLoading: (loading) => set({ loading }),

      logout: () => set({ user: null, accessToken: null, refreshToken: null, loading: false }),

      isAuthenticated: () => !!get().accessToken && !!get().user,

      hasRole: (role) => {
        const user = get().user
        if (!user) return false
        return user.role?.toLowerCase() === role.toLowerCase()
      },

      isAdmin: () => get().user?.role?.toLowerCase() === 'admin',
      isCoach: () => get().user?.role?.toLowerCase() === 'coach',

      login: async ({ email, password }) => {
        set({ loading: true })
        try {
          const res = await axios.post(`${API_BASE}/auth/login`, { email, password })
          const { user, access_token, refresh_token } = res.data
          set({ user, accessToken: access_token, refreshToken: refresh_token, loading: false })
          return { user, accessToken: access_token, refreshToken: refresh_token }
        } catch (err) {
          set({ loading: false })
          const msg = err.response?.data?.detail || err.message || 'Login failed'
          throw new Error(msg)
        }
      },

      validateSession: async () => {
        const { accessToken, refreshToken } = get()
        if (!accessToken && !refreshToken) {
          set({ loading: false })
          return
        }
        set({ loading: true })
        try {
          const res = await axios.get(`${API_BASE}/auth/me`, {
            headers: { Authorization: `Bearer ${accessToken}` },
          })
          set({ user: res.data, loading: false })
        } catch (err) {
          // try refresh if 401 and has refresh token
          if (err.response?.status === 401 && refreshToken) {
            try {
              const refreshRes = await axios.post(`${API_BASE}/auth/refresh`, {
                refresh_token: refreshToken,
              })
              const { access_token, refresh_token: newRefresh } = refreshRes.data
              set({ accessToken: access_token, refreshToken: newRefresh || refreshToken })
              const retry = await axios.get(`${API_BASE}/auth/me`, {
                headers: { Authorization: `Bearer ${access_token}` },
              })
              set({ user: retry.data, loading: false })
              return
            } catch {
              // refresh failed
            }
          }
          set({ user: null, accessToken: null, refreshToken: null, loading: false })
        }
      },
    }),
    {
      name: 'tennis-explore-auth',
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
      }),
    }
  )
)
