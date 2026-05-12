import { Input } from '@/components/ui/input'
import { Icon } from '@/components/shared/icon'
import { cn } from '@/lib/utils'

export function SearchInput({ placeholder = 'Search...', className, inputClassName, ...props }) {
  return (
    <div className={cn('relative', className)}>
      <Icon name="search" className="absolute left-3 top-1/2 -translate-y-1/2 text-te-outline text-sm" />
      <Input
        className={cn('pl-10 bg-te-surface-container-low', inputClassName)}
        placeholder={placeholder}
        {...props}
      />
    </div>
  )
}
