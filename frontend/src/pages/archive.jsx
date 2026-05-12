import { Icon } from '@/components/shared'

export default function ArchivePage() {
  return (
    <div className="flex items-center justify-center h-[calc(100vh-10rem)]">
      <div className="text-center">
        <div className="w-20 h-20 bg-muted rounded-2xl flex items-center justify-center mx-auto mb-6">
          <Icon name="construction" className="text-5xl text-te-outline-variant" />
        </div>
        <h2 className="text-headline-lg text-foreground">Archive</h2>
        <p className="text-muted-foreground mt-2 max-w-md">
          This section is under construction. Historical match data and archived analytics reports will be available here soon.
        </p>
      </div>
    </div>
  )
}
