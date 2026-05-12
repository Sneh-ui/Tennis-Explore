import { cn } from '@/lib/utils'

export function ProgressBar({ label, value, color = 'bg-primary', className }) {
  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex justify-between text-[11px] font-bold text-muted-foreground uppercase tracking-wider">
        <span>{label}</span>
        <span className="text-foreground">{value}%</span>
      </div>
      <div className="w-full bg-muted h-2.5 rounded-full overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all duration-700', color)}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  )
}
