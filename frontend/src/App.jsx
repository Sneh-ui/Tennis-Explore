import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { lazy, Suspense } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { TooltipProvider } from '@/components/ui/tooltip'
import { AppLayout, ProtectedRoute } from '@/components/layout'
import { RoleGuard } from '@/components/layout/role-guard'
import { AuthProvider } from '@/context/auth-provider'
import { queryClient } from '@/lib/query-client'
import { PageSkeleton } from '@/components/ui/skeleton'

const TennisExploreHero = lazy(() => import('@/pages/TennisExploreHero'))
const LoginPage = lazy(() => import('@/pages/login'))
const MediaLibraryPage = lazy(() => import('@/pages/media-library'))
const AIChatbotPage = lazy(() => import('@/pages/ai-chatbot'))
const AdminUsersPage = lazy(() => import('@/pages/admin-users'))
const DashboardPage = lazy(() => import('@/pages/dashboard'))
const DataPortalPage = lazy(() => import('@/pages/data-portal'))
const ArchivePage = lazy(() => import('@/pages/archive'))

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <TooltipProvider>
          <BrowserRouter>
            <Suspense fallback={<PageSkeleton />}>
              <Routes>
                <Route path="/" element={<TennisExploreHero />} />
                <Route path="/login" element={<LoginPage />} />
                <Route element={<ProtectedRoute />}>
                  <Route element={<AppLayout />}>
                    <Route
                      path="/media-library"
                      element={
                        <RoleGuard allowedRoles={['admin', 'coach']}>
                          <MediaLibraryPage />
                        </RoleGuard>
                      }
                    />
                    <Route
                      path="/ai-chatbot"
                      element={
                        <RoleGuard allowedRoles={['admin', 'coach']}>
                          <AIChatbotPage />
                        </RoleGuard>
                      }
                    />
                    <Route
                      path="/users"
                      element={
                        <RoleGuard allowedRoles={['admin']}>
                          <AdminUsersPage />
                        </RoleGuard>
                      }
                    />
                    {/* <Route path="/dashboard" element={<RoleGuard allowedRoles={['admin','coach']}><DashboardPage /></RoleGuard>} /> */}
                    {/* <Route path="/data-portal" element={<RoleGuard allowedRoles={['admin','coach']}><DataPortalPage /></RoleGuard>} /> */}
                    {/* <Route path="/archive" element={<RoleGuard allowedRoles={['admin']}><ArchivePage /></RoleGuard>} /> */}
                  </Route>
                </Route>
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Suspense>
          </BrowserRouter>
        </TooltipProvider>
      </AuthProvider>
    </QueryClientProvider>
  )
}
