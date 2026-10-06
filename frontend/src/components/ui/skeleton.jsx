import { cn } from '@/lib/utils'

export function Skeleton({ className, ...props }) {
  return <div className={cn('animate-pulse rounded-md bg-muted', className)} {...props} />
}

export function TableSkeleton({ rows = 5, cols = 4 }) {
  return (
    <div className="space-y-3">
      <Skeleton className="h-10 w-full" />
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4">
          {Array.from({ length: cols }).map((_, j) => (
            <Skeleton key={j} className="h-12 flex-1" />
          ))}
        </div>
      ))}
    </div>
  )
}

export function CardSkeleton() {
  return (
    <div className="rounded-xl border border-te-outline-variant bg-card p-6 space-y-4">
      <Skeleton className="h-6 w-1/3" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-2/3" />
    </div>
  )
}

export function PageSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <Skeleton className="h-8 w-1/4" />
      <Skeleton className="h-4 w-1/3" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <CardSkeleton />
        <CardSkeleton />
      </div>
    </div>
  )
}
