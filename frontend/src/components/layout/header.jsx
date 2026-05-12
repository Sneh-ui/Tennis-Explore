import { Icon } from '@/components/shared/icon'
import { SearchInput } from '@/components/shared/search-input'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar'
import { Separator } from '@/components/ui/separator'
import { PROFILE_IMG } from '@/data/constants'

export function Header({ onMenuClick }) {
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
        <div className="flex items-center gap-3">
          <div className="hidden sm:block text-right">
            <p className="text-xs font-bold text-foreground leading-none">Alex Rivera</p>
            <p className="text-label-md text-muted-foreground">Lead Analyst</p>
          </div>
          <Avatar className="h-9 w-9 border-2 border-primary-container">
            <AvatarImage src={PROFILE_IMG} alt="Alex Rivera" />
            <AvatarFallback>AR</AvatarFallback>
          </Avatar>
        </div>
      </div>
    </header>
  )
}
