import { Icon } from '@/components/shared/icon'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'

export function DataTable({ columns, data, currentPage = 1, totalItems = 0, onPageChange, className }) {
  const totalPages = Math.ceil(totalItems / data.length) || 3

  return (
    <Card className={cn('overflow-hidden', className)}>
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-te-outline-variant bg-te-surface-container-low">
              {columns.map((col, i) => (
                <th
                  key={col.key}
                  className={cn(
                    'px-6 py-4 font-bold text-muted-foreground uppercase tracking-wider text-[11px]',
                    col.align === 'center' && 'text-center'
                  )}
                >
                  <div className={cn('flex items-center gap-1', col.sortable && 'cursor-pointer hover:text-primary')}>
                    {col.label}
                    {col.sortable && <Icon name="arrow_upward" className="text-xs" />}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="text-body-md text-foreground">
            {data.map((row, rowIdx) => (
              <tr
                key={rowIdx}
                className={cn(
                  'border-b border-te-outline-variant/30 hover:bg-te-surface-container-low transition-colors',
                  rowIdx % 2 === 1 && 'bg-te-surface-container-low'
                )}
              >
                {columns.map((col) => (
                  <td key={col.key} className={cn('px-6 py-5', col.align === 'center' && 'text-center')}>
                    {col.render ? col.render(row[col.key], row) : row[col.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalItems > 0 && (
        <div className="p-6 bg-te-surface-container-low border-t border-te-outline-variant flex items-center justify-between">
          <p className="text-label-md text-muted-foreground">
            Showing 1-{data.length} of {totalItems} matches
          </p>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="icon" className="w-10 h-10 rounded-lg" onClick={() => onPageChange?.(Math.max(1, currentPage - 1))}>
              <Icon name="chevron_left" />
            </Button>
            {Array.from({ length: totalPages }, (_, i) => i + 1).map(p => (
              <Button
                key={p}
                variant={currentPage === p ? 'default' : 'outline'}
                size="icon"
                className="w-10 h-10 rounded-lg font-bold"
                onClick={() => onPageChange?.(p)}
              >
                {p}
              </Button>
            ))}
            <Button variant="outline" size="icon" className="w-10 h-10 rounded-lg" onClick={() => onPageChange?.(Math.min(totalPages, currentPage + 1))}>
              <Icon name="chevron_right" />
            </Button>
          </div>
        </div>
      )}
    </Card>
  )
}
