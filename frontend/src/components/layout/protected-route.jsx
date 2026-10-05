import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/hooks/use-auth'
import { Icon } from '@/components/shared/icon'

export function ProtectedRoute() {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="flex flex-col items-center gap-3">
          <Icon name="progress_activity" className="animate-spin text-3xl text-primary" />
          <p className="text-sm text-muted-foreground">Validating session...</p>
        </div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return <Outlet />
}

export function AdminRoute() {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="flex flex-col items-center gap-3">
          <Icon name="progress_activity" className="animate-spin text-3xl text-primary" />
          <p className="text-sm text-muted-foreground">Validating session...</p>
        </div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  const isAdmin = (user.role || '').toLowerCase() === 'admin'
  if (!isAdmin) {
    return <Navigate to="/ai-chatbot" replace />
  }

  return <Outlet />
}
