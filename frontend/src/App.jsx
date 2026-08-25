import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { TooltipProvider } from '@/components/ui/tooltip'
import { AppLayout, ProtectedRoute } from '@/components/layout'
import { AuthProvider } from '@/context/auth-provider'
import { DashboardPage, TennisExploreHero, DataPortalPage, MediaLibraryPage, AIChatbotPage, ArchivePage, LoginPage } from '@/pages'

export default function App() {
  return (
    <AuthProvider>
      <TooltipProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<TennisExploreHero />} />
            <Route path="/login" element={<LoginPage />} />
            <Route element={<ProtectedRoute />}>
              <Route element={<AppLayout />}>
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/data-portal" element={<DataPortalPage />} />
                <Route path="/media-library" element={<MediaLibraryPage />} />
                <Route path="/ai-chatbot" element={<AIChatbotPage />} />
                <Route path="/archive" element={<ArchivePage />} />
              </Route>
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </AuthProvider>
  )
}
