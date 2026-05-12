import { cn } from '@/lib/utils'

export function Icon({ name, className, filled = false, ...props }) {
  return (
    <span
      className={cn('material-symbols-outlined', filled && 'filled', className)}
      {...props}
    >
      {name}
    </span>
  )
}
