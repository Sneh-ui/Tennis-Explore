import { Card } from '@/components/ui/card'
import { Icon } from '@/components/shared/icon'
import { cn } from '@/lib/utils'

export function InsightCard({ label, value, subtext, subtextIcon, subtextColor = 'text-primary', borderColor = 'bg-primary', className }) {
  return (
    <Card className={cn('p-6 relative overflow-hidden group hover:shadow-md transition-shadow', className)}>
      <div className={cn('absolute left-0 top-0 h-full w-1', borderColor)} />
      <p className="text-muted-foreground font-bold uppercase text-[10px] tracking-widest mb-2">{label}</p>
      <h3 className="text-stats-xl text-foreground">{value}</h3>
      <div className={cn('mt-4 flex items-center gap-2 font-bold text-sm', subtextColor)}>
        <Icon name={subtextIcon} className="text-sm" />
        {subtext}
      </div>
    </Card>
  )
}
