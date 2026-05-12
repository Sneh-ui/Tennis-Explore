import { Card } from '@/components/ui/card'
import { Icon } from '@/components/shared/icon'
import { cn } from '@/lib/utils'

export function StatCard({ label, value, subtext, icon, subtextColor = 'text-primary', subtextIcon, className }) {
  return (
    <Card className={cn('p-6 flex flex-col justify-between hover:border-primary transition-colors cursor-default group', className)}>
      <div className="flex justify-between items-start mb-4">
        <span className="text-muted-foreground text-[10px] font-bold uppercase tracking-wider">{label}</span>
        <div className="bg-primary/10 p-2 rounded-lg group-hover:bg-primary transition-colors">
          <Icon name={icon} className="text-primary text-xl group-hover:text-white transition-colors" />
        </div>
      </div>
      <div>
        <div className="text-stats-xl text-foreground">{value}</div>
        <div className={cn('text-xs font-semibold mt-1 flex items-center gap-1', subtextColor)}>
          {subtextIcon && <Icon name={subtextIcon} className="text-sm" />}
          {subtext}
        </div>
      </div>
    </Card>
  )
}
