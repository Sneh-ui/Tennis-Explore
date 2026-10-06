import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/axios'

export function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: async () => {
      const res = await api.get('/auth/users')
      return res.data
    },
  })
}

export function useCreateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (payload) => {
      const res = await api.post('/auth/users', payload)
      return res.data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })
}

export function useUpdateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, ...payload }) => {
      const res = await api.put(`/auth/users/${id}`, payload)
      return res.data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })
}

export function useDeleteUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id) => {
      await api.delete(`/auth/users/${id}`)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })
}

export function useUpdatePassword() {
  return useMutation({
    mutationFn: async ({ current_password, new_password }) => {
      const res = await api.put('/auth/me/password', {
        current_password,
        new_password,
      })
      return res.data
    },
  })
}
