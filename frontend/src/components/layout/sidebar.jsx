import { useLocation, useNavigate } from 'react-router-dom'
import { Icon } from '@/components/shared/icon'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { NAV_ITEMS } from '@/data/constants'
import { cn } from '@/lib/utils'

export function Sidebar({ mobileOpen, onCloseMobile }) {
  const location = useLocation()
  const navigate = useNavigate()

  const handleNavigate = (path) => {
    navigate(path)
    onCloseMobile?.()
  }

  return (
    <>
      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 bg-black/40 z-40 md:hidden" onClick={onCloseMobile} />
      )}

      <aside
        className={cn(
          'fixed md:static z-50 h-screen w-64 border-r border-te-outline-variant bg-te-surface-container-low py-4 flex flex-col shrink-0 transition-transform duration-300',
          mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        )}
      >
        {/* Brand */}
        <div className="flex justify-center items-center mb-3">
          <img src="/images/tennis-australia-logo.svg" />
        </div>

        {/* Navigation */}
        <ScrollArea className="flex-1 px-3">
          <nav className="space-y-1">
            {NAV_ITEMS.map((item) => {
              const isActive = location.pathname === item.path
              return (
                <button
                  key={item.id}
                  onClick={() => handleNavigate(item.path)}
                  className={cn(
                    'w-full flex items-center px-4 py-3 text-left transition-all duration-200 text-label-md',
                    isActive
                      ? 'bg-te-surface-container-highest text-primary border-l-4 border-primary shadow-sm'
                      : 'text-muted-foreground hover:text-foreground hover:bg-te-surface-container-high border-l-4 border-transparent'
                  )}
                >
                  <Icon name={item.icon} className="mr-3 text-xl" />
                  {item.label}
                </button>
              )
            })}
          </nav>
        </ScrollArea>

        {/* Footer */}
        <div className="px-3 pt-4 mt-4">
          <Separator className="mb-4" />
          {/* <Button className="w-full" size="lg">
            <Icon name="add" className="text-sm" />
            New Analysis
          </Button> */}
          <button className="flex items-center px-4 py-3 mt-4 text-muted-foreground hover:text-foreground w-full text-left text-label-md transition-colors">
            <Icon name="help_outline" className="mr-3" />
            Help Center
          </button>
        </div>
      </aside>
    </>
  )
}
