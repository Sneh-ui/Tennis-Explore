import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useEffect, useState, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Icon, PageHeader, SearchInput, MediaCard } from '@/components/shared'
import {
  getMediaFiles,
  getMediaUrl,
  getPowerPointPreview,
  getMediaThumbnail,
} from '@/lib/media-api'

function formatSize(bytes) {
  if (bytes == null) return 'Unknown size'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function MediaLibraryPage() {
  const [category, setCategory] = useState('all')
  const [search, setSearch] = useState('')
  const [items, setItems] = useState([])
  const [cursor, setCursor] = useState(null)
  const [loading, setLoading] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState('')
  const [selectedMedia, setSelectedMedia] = useState(null)
  const [previewUrl, setPreviewUrl] = useState('')
  const [previewLoading, setPreviewLoading] = useState(false)
  const [imageUrls, setImageUrls] = useState({})
  const [thumbnailUrls, setThumbnailUrls] = useState({})
  const thumbnailCache = useRef({})
  const thumbnailFailures = useRef(new Set())

  useEffect(() => {
    let cancelled = false

    async function loadFiles() {
      setLoading(true)
      setError('')
      setItems([])
      setCursor(null)

      try {
        const result = await getMediaFiles({
          category,
          search,
          limit: 24,
        })

        if (!cancelled) {
          setItems(result.items || [])
          setCursor(result.next_cursor || null)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.response?.data?.detail || err.message)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    const timer = setTimeout(loadFiles, search ? 300 : 0)

    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [category, search])

  useEffect(() => {
    let cancelled = false

    const documents = items.filter(
      (item) =>
        (item.type === 'pdf' || /\.(ppt|pptx)$/i.test(item.title)) &&
        !thumbnailCache.current[item.id] &&
        !thumbnailFailures.current.has(item.id)
    )

    async function loadThumbnails() {
      for (const item of documents) {
        if (cancelled) break

        try {
          const url = await getMediaThumbnail(item.id)

          if (cancelled) {
            URL.revokeObjectURL(url)
            break
          }

          thumbnailCache.current[item.id] = url
          setThumbnailUrls((previous) => ({
            ...previous,
            [item.id]: url,
          }))
        } catch (err) {
          thumbnailFailures.current.add(item.id)
          console.error('Thumbnail failed:', item.title, err)
        }
      }
    }

    loadThumbnails()

    return () => {
      cancelled = true
    }
  }, [items])


  async function loadMore() {
    if (!cursor || loadingMore) return

    setLoadingMore(true)
    setError('')

    try {
      const result = await getMediaFiles({
        category,
        search,
        limit: 24,
        cursor,
      })

      setItems((previous) => [...previous, ...(result.items || [])])
      setCursor(result.next_cursor || null)
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setLoadingMore(false)
    }
  }

  useEffect(() => {
  let cancelled = false

  const images = items.filter(
    (item) => item.type === 'image' && !imageUrls[item.id]
  )

  if (images.length === 0) return

  async function loadThumbnails() {
    const results = await Promise.allSettled(
      images.map(async (item) => ({
        id: item.id,
        url: (await getMediaUrl(item.id, false)).url,
      }))
    )

    if (cancelled) return

    const newUrls = {}

    results.forEach((result) => {
      if (result.status === 'fulfilled') {
        newUrls[result.value.id] = result.value.url
      }
    })

    if (Object.keys(newUrls).length > 0) {
      setImageUrls((previous) => ({ ...previous, ...newUrls }))
    }
  }

  loadThumbnails()

  return () => {
    cancelled = true
  }
}, [items])

async function openMedia(item) {
  setSelectedMedia(item)
  setPreviewUrl('')
  setPreviewLoading(true)
  setError('')

  const filename = item.title.toLowerCase()

  const isPowerPoint =
  filename.endsWith('.ppt') || filename.endsWith('.pptx')

  const canPreview = isPowerPoint || [
    '.pdf', '.jpg', '.jpeg', '.png',
    '.webp', '.mp4', '.webm',
  ].some((ext) => filename.endsWith(ext))

  if (!canPreview) {
    setPreviewLoading(false)
    return
  }

  try {
    if (isPowerPoint) {
      const pdfUrl = await getPowerPointPreview(item.id)
      setPreviewUrl(pdfUrl)
    } else {
      const result = await getMediaUrl(item.id, false)
      setPreviewUrl(result.url)
    }
  } catch (err) {
    setError(err.response?.data?.detail || err.message)
  } finally {
    setPreviewLoading(false)
  }
}

async function downloadMedia() {
  if (!selectedMedia) return

  try {
    const result = await getMediaUrl(selectedMedia.id, true)
    const link = document.createElement('a')
    link.href = result.url
    link.download = selectedMedia.title
    document.body.appendChild(link)
    link.click()
    link.remove()
  } catch (err) {
    setError(err.response?.data?.detail || err.message)
  }
}


  return (
    <div className="space-y-6">
      <PageHeader
        title="Library"
        titleSize="text-display-lg"
        subtitle="Manage and analyze your collection of tennis performance media."
        actions={
          <div className="flex flex-wrap items-center gap-4">
            <SearchInput
              placeholder="Search media files..."
              className="min-w-[280px]"
              inputClassName="py-3 h-auto bg-card"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
        }
      />

      <Tabs value={category} onValueChange={setCategory} className="w-full">
        <div className="flex items-center justify-between pb-4 border-b border-te-outline-variant/50">
          <TabsList>
            <TabsTrigger value="all">All Files</TabsTrigger>
            <TabsTrigger value="videos">Videos</TabsTrigger>
            <TabsTrigger value="images">Images</TabsTrigger>
            <TabsTrigger value="documents">Documents</TabsTrigger>
          </TabsList>
        </div>
      </Tabs>

      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}

      {loading ? (
        <p className="text-muted-foreground">Loading media files...</p>
      ) : items.length === 0 ? (
        <p className="text-muted-foreground">
          No media files found.
        </p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-gutter">
          {items.map((item) => (
            <div
              key={item.id}
              role="button"
              tabIndex={0}
              onClick={() => openMedia(item)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault()
                  openMedia(item)
                }
              }}
            >
              <MediaCard
                item={{
                  ...item,
                  size: formatSize(item.size_bytes),
                  thumbnailUrl: thumbnailUrls[item.id] || null,
                  subtitle: item.type === 'pdf' ? 'PDF DOCUMENT' : 'DOCUMENT',
                }}
              />
            </div>
          ))}
        </div>
      )}

      {cursor && !loading && (
        <div className="flex justify-center">
          <Button onClick={loadMore} disabled={loadingMore}>
            {loadingMore ? 'Loading...' : 'Load More'}
          </Button>
        </div>
      )}
          <Dialog
        open={!!selectedMedia}
        onOpenChange={(open) => {
          if (!open) {
            setSelectedMedia(null)
            setPreviewUrl('')
          }
        }}
      >
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle className="truncate">
              {selectedMedia?.title || 'Media Preview'}
            </DialogTitle>
          </DialogHeader>

          <div className="min-h-[250px] max-h-[65vh] overflow-auto bg-card rounded-lg flex items-center justify-center">
            {previewLoading ? (
              <p className="text-muted-foreground">
                Loading preview...
              </p>
            ) : previewUrl && selectedMedia?.type === 'image' ? (
              <img
                src={previewUrl}
                alt={selectedMedia.title}
                className="max-h-[60vh] max-w-full object-contain"
              />
            ) : previewUrl && selectedMedia?.type === 'video' ? (
              <video
                src={previewUrl}
                controls
                className="max-h-[60vh] max-w-full"
              />
            ) : previewUrl && (
              selectedMedia?.type === 'pdf' ||
              /\.(ppt|pptx)$/i.test(selectedMedia?.title || '')
            ) ? (
              <iframe
                src={previewUrl}
                title={selectedMedia.title}
                className="w-full h-[60vh] border-0"
              />
            ) : (
              <div className="text-center p-8">
                <p className="font-semibold mb-2">
                  {selectedMedia?.title}
                </p>
                <p className="text-muted-foreground text-sm">
                  Preview is not available for this file type.
                  You can download the file instead.
                </p>
              </div>
            )}
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <Button
              variant="outline"
              onClick={() => setSelectedMedia(null)}
            >
              Close
            </Button>

            <Button onClick={downloadMedia}>
              <Icon name="download" className="mr-2" />
              Download
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
