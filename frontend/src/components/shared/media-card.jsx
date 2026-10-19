
import { Card } from '@/components/ui/card'
import { Icon } from '@/components/shared/icon'
import { cn } from '@/lib/utils'

const TYPE_STYLES = {
  video: { bg: 'bg-primary/10', text: 'text-primary' },
  pdf: { bg: 'bg-destructive/10', text: 'text-destructive' },
  image: { bg: 'bg-tertiary/10', text: 'text-tertiary' },
  document: { bg: 'bg-primary/10', text: 'text-primary' },
}

export function MediaCard({ item }) {
  const tc = TYPE_STYLES[item.type] || TYPE_STYLES.document

  return (
    <Card
      className={cn(
        'group relative overflow-hidden cursor-pointer hover:-translate-y-1 transition-all duration-300',
        'hover:border-primary/40 hover:shadow-lg'
      )}
    >
      {/* Media preview */}
      <div className="aspect-[16/10] relative overflow-hidden bg-te-surface-container-low flex items-center justify-center">
        {item.thumbnailUrl ? (
          <div className="absolute inset-0 overflow-hidden bg-te-surface-container-low">
            <img
              src={item.thumbnailUrl}
              alt={`Preview of ${item.title}`}
              loading="lazy"
              className="w-full h-full object-cover object-top"
            />
          </div>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center bg-te-surface-container-low">
            <div className={cn('rounded-2xl p-6', tc.bg, tc.text)}>
              <Icon
                name={
                  item.type === 'video'
                    ? 'videocam'
                    : item.type === 'image'
                      ? 'image'
                      : item.type === 'pdf'
                        ? 'picture_as_pdf'
                        : 'description'
                }
                className="text-6xl"
              />
            </div>
          </div>
        )}
          </div>
        
        
      

      {/* File information */}
      <div className="p-5">
        <h3 className="text-sm font-bold text-foreground mb-2 truncate" title={item.title}>
          {item.title}
        </h3>

        <div className="flex items-center justify-between">
          <span className={cn('px-2 py-1 text-[10px] font-bold rounded-md uppercase', tc.bg, tc.text)}>
            {item.type}
          </span>

          <p className="text-[10px] font-medium text-muted-foreground">
            {item.size}
          </p>
        </div>
      </div>
    </Card>
  )
}
