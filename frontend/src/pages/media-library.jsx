import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Icon, PageHeader, SearchInput, MediaCard } from '@/components/shared'
import { MEDIA_ITEMS } from '@/data/constants'

export default function MediaLibraryPage() {
  const filterItems = (type) => {
    if (type === 'all') return MEDIA_ITEMS
    const typeMap = { videos: 'video', images: 'image', documents: 'pdf' }
    return MEDIA_ITEMS.filter((item) => item.type === typeMap[type])
  }

  const MediaGrid = ({ items }) => (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-gutter">
      {items.map((item, i) => (
        <MediaCard key={i} item={item} />
      ))}
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="Library"
        titleSize="text-display-lg"
        subtitle="Manage and analyze your collection of tennis performance media."
        actions={
          <div className="flex flex-wrap items-center gap-4">
            <SearchInput placeholder="Search media files..." className="min-w-[280px]" inputClassName="py-3 h-auto bg-card" />
            <Button size="lg">
              <Icon name="add" className="text-lg" /> ADD MEDIA
            </Button>
          </div>
        }
      />

      <Tabs defaultValue="all" className="w-full">
        <div className="flex items-center justify-between pb-4 border-b border-te-outline-variant/50">
          <TabsList>
            <TabsTrigger value="all">All Files</TabsTrigger>
            <TabsTrigger value="videos">Videos</TabsTrigger>
            <TabsTrigger value="images">Images</TabsTrigger>
            <TabsTrigger value="documents">Documents</TabsTrigger>
          </TabsList>

          <div className="flex bg-muted p-1 rounded-lg">
            <button className="p-2 bg-card shadow-sm rounded-md text-primary">
              <Icon name="grid_view" className="text-xl" />
            </button>
            <button className="p-2 text-muted-foreground hover:text-foreground transition-colors">
              <Icon name="list" className="text-xl" />
            </button>
          </div>
        </div>

        <TabsContent value="all">
          <MediaGrid items={filterItems('all')} />
        </TabsContent>
        <TabsContent value="videos">
          <MediaGrid items={filterItems('videos')} />
        </TabsContent>
        <TabsContent value="images">
          <MediaGrid items={filterItems('images')} />
        </TabsContent>
        <TabsContent value="documents">
          <MediaGrid items={filterItems('documents')} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
