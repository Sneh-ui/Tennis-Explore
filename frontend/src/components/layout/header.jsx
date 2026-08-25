import { useNavigate } from 'react-router-dom'
import { Icon } from '@/components/shared/icon'
import { SearchInput } from '@/components/shared/search-input'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Separator } from '@/components/ui/separator'
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'
import { useAuth } from '@/hooks/use-auth'

const getInitials = (name) =>
  name
    .split(' ')
    .filter(Boolean)
    .map((part) => part[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()

export function Header({ onMenuClick }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleSignOut = () => {
    logout()
    navigate('/', { replace: true })
  }

  return (
    <header className="flex justify-between items-center w-full px-6 h-16 bg-card border-b border-te-outline-variant shrink-0">
      {/* Left side */}
      <div className="flex items-center gap-4 flex-1">
        <Button variant="ghost" size="icon" className="md:hidden" onClick={onMenuClick}>
          <Icon name="menu" className="text-foreground" />
        </Button>
        <div className="text-xl font-black tracking-tight text-primary uppercase">Tennis Explore</div>
        <SearchInput
          placeholder="Search matches, players, or clips..."
          className="max-w-md w-full ml-8 hidden lg:block"
        />
      </div>

      {/* Right side */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" className="relative">
          <Icon name="notifications" className="text-muted-foreground" />
          <span className="absolute top-2 right-2 w-2 h-2 bg-destructive rounded-full border-2 border-card" />
        </Button>
        <Button variant="ghost" size="icon">
          <Icon name="settings" className="text-muted-foreground" />
        </Button>
        <Separator orientation="vertical" className="h-8" />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              aria-label="Open profile menu"
              className="flex items-center gap-3 rounded-full outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            >
              <div className="hidden sm:block text-right">
                <p className="text-xs font-bold text-foreground leading-none">{user?.name}</p>
                <p className="text-label-md text-muted-foreground">{user?.role}</p>
              </div>
              <Avatar className="h-9 w-9 border-2 border-primary-container">
                <AvatarFallback>{getInitials(user?.name ?? 'TE')}</AvatarFallback>
              </Avatar>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>{user?.email}</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleSignOut}>
              <Icon name="logout" className="text-muted-foreground" />
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
