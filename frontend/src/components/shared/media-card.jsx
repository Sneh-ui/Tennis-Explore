import { Card } from '@/components/ui/card'
import { Icon } from '@/components/shared/icon'
import { cn } from '@/lib/utils'

const TYPE_STYLES = {
  video: { bg: 'bg-primary/10', text: 'text-primary' },
  pdf: { bg: 'bg-destructive/10', text: 'text-destructive' },
  image: { bg: 'bg-tertiary/10', text: 'text-tertiary' },
}

export function MediaCard({ item }) {
  const tc = TYPE_STYLES[item.type] || TYPE_STYLES.video

  return (
    <Card
      className={cn(
        'group relative overflow-hidden cursor-pointer transform hover:-translate-y-1 transition-all duration-300',
        item.selected
          ? 'border-2 border-primary shadow-xl shadow-primary/5'
          : 'hover:border-primary/40 hover:shadow-lg'
      )}
    >
      {/* Selection checkbox */}
      <div className={cn('absolute top-4 right-4 z-10', !item.selected && 'opacity-0 group-hover:opacity-100 transition-opacity')}>
        <div className={cn(
          'w-6 h-6 rounded-lg border-2 flex items-center justify-center',
          item.selected ? 'border-primary bg-primary text-white' : 'border-te-outline-variant bg-card'
        )}>
          {item.selected && <Icon name="check" className="text-sm font-bold" />}
        </div>
      </div>

      {/* Preview area */}
      <div className="aspect-[16/10] relative overflow-hidden">
        {item.type === 'video' && (
          <>
            <img className="w-full h-full object-cover opacity-60 group-hover:scale-110 transition-transform duration-700 bg-foreground" src={item.img} alt={item.title} />
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
            <Icon name="play_circle" className="absolute inset-0 m-auto text-white text-5xl drop-shadow-lg" filled />
            <div className="absolute bottom-3 right-3 px-2 py-1 bg-black/80 backdrop-blur-sm text-white text-[10px] rounded-md font-bold tracking-wider">{item.duration}</div>
          </>
        )}
        {item.type === 'pdf' && (
          <div className="w-full h-full bg-te-surface-container-low flex flex-col items-center justify-center">
            <div className="w-16 h-16 bg-destructive/10 rounded-2xl flex items-center justify-center mb-3">
              <Icon name="picture_as_pdf" className="text-destructive text-4xl" />
            </div>
            <p className="text-[10px] font-black text-muted-foreground uppercase tracking-widest">{item.subtitle}</p>
          </div>
        )}
        {item.type === 'image' && (
          <img className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700 opacity-90 bg-foreground" src={item.img} alt={item.title} />
        )}
      </div>

      {/* Info footer */}
      <div className="p-5">
        <h3 className="text-sm font-bold text-foreground mb-2 truncate">{item.title}</h3>
        <div className="flex items-center justify-between">
          <span className={cn('px-2 py-1 text-[10px] font-bold rounded-md uppercase', tc.bg, tc.text)}>{item.type}</span>
          <p className="text-[10px] font-medium text-muted-foreground">{item.size}</p>
        </div>
      </div>
    </Card>
  )
}
