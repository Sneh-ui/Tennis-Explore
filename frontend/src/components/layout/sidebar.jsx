import { useLocation, useNavigate } from 'react-router-dom'
import { Icon } from '@/components/shared/icon'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { NAV_ITEMS, ADMIN_NAV_ITEM, EXTERNAL_APPS } from '@/data/constants'
import { useAuth } from '@/hooks/use-auth'
import { cn } from '@/lib/utils'

export function Sidebar({ mobileOpen, onCloseMobile }) {
  const location = useLocation()
  const navigate = useNavigate()
  const { user } = useAuth()
  const isAdmin = (user?.role || '').toLowerCase() === 'admin'
  const navItems = isAdmin ? [...NAV_ITEMS, ADMIN_NAV_ITEM] : NAV_ITEMS

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
            {navItems.map((item) => {
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

          {/* External Apps — separate section */}
          <div className="mt-6">
            <Separator className="mb-4" />
            <p className="px-4 mb-2 text-[11px] font-semibold tracking-[0.14em] text-muted-foreground uppercase">
              Our Own Apps
            </p>
            <nav className="space-y-0.5">
              {EXTERNAL_APPS.map((app) => {
                const disabled = !app.url
                return (
                  <a
                    key={app.id}
                    href={app.url || undefined}
                    target={app.url ? '_blank' : undefined}
                    rel={app.url ? 'noopener noreferrer' : undefined}
                    onClick={(e) => {
                      if (disabled) e.preventDefault()
                    }}
                    aria-disabled={disabled}
                    title={disabled ? `${app.label} — coming soon` : app.label}
                    className={cn(
                      'w-full flex items-center justify-between px-4 py-2.5 text-left transition-colors text-label-md rounded-md border-l-4',
                      disabled
                        ? 'text-muted-foreground/50 cursor-not-allowed border-transparent'
                        : 'text-muted-foreground hover:text-foreground hover:bg-te-surface-container-high border-transparent hover:border-primary/30'
                    )}
                  >
                    <span className="flex items-center min-w-0">
                      <Icon
                        name={app.icon}
                        filled={!!app.filled}
                        className={cn('mr-3 text-xl shrink-0', app.bold && 'font-bold')}
                      />
                      <span className={cn('truncate', app.bold && 'font-semibold')}>{app.label}</span>
                    </span>
                    {!disabled && <Icon name="open_in_new" className="ml-2 text-[16px] opacity-60 shrink-0" />}
                  </a>
                )
              })}
            </nav>
          </div>
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
