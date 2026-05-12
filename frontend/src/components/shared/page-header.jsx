import { cn } from '@/lib/utils'

export function PageHeader({ title, subtitle, actions, className, titleSize = 'text-headline-lg' }) {
  return (
    <div className={cn('flex flex-col md:flex-row justify-between items-start md:items-end gap-4', className)}>
      <div>
        <h2 className={cn(titleSize, 'text-foreground')}>{title}</h2>
        {subtitle && <p className="text-muted-foreground text-body-md">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  )
}
