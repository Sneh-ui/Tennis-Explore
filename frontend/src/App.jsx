import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { TooltipProvider } from '@/components/ui/tooltip'
import { AppLayout } from '@/components/layout'
import { DashboardPage, TennisExploreHero, DataPortalPage, MediaLibraryPage, AIChatbotPage, ArchivePage } from '@/pages'

export default function App() {
  return (
    <TooltipProvider>
      <BrowserRouter>
        <Routes>
         <Route path="/" element={<TennisExploreHero />} />
          <Route element={<AppLayout />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/data-portal" element={<DataPortalPage />} />
            <Route path="/media-library" element={<MediaLibraryPage />} />
            <Route path="/ai-chatbot" element={<AIChatbotPage />} />
            <Route path="/archive" element={<ArchivePage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  )
}
