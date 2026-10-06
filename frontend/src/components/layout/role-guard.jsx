import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/hooks/use-auth'
import { Icon } from '@/components/shared/icon'

export function RoleGuard({ allowedRoles, children }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-10rem)]">
        <div className="flex flex-col items-center gap-3">
          <Icon name="progress_activity" className="animate-spin text-3xl text-primary" />
          <p className="text-sm text-muted-foreground font-sans">Validating session...</p>
        </div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  const userRole = user.role?.toLowerCase()
  const allowed = allowedRoles.map((r) => r.toLowerCase())

  if (!allowed.includes(userRole)) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-10rem)]">
        <div className="text-center max-w-md p-8 rounded-xl border border-te-outline-variant bg-card">
          <Icon name="block" className="text-4xl text-destructive mx-auto mb-4" />
          <h2 className="text-headline-md text-foreground font-sans">Access Denied</h2>
          <p className="text-muted-foreground mt-2 font-sans">Your role <span className="font-bold">{user.role}</span> cannot access this page. Required: {allowedRoles.join(', ')}</p>
        </div>
      </div>
    )
  }

  return children ? children : <Outlet />
}
