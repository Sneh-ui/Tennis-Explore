
import api from '@/lib/axios'

const MEDIA_BASE = import.meta.env.VITE_MEDIA_API_URL || import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

// Retrieve media files from AWS S3
export async function getMediaFiles({
  category = 'all',
  search = '',
  limit = 24,
  cursor = null,
} = {}) {
  const response = await api.get(`${MEDIA_BASE}/api/media`, {
    params: {
      category,
      search,
      limit,
      ...(cursor ? { cursor } : {}),
    },
  })

  return response.data
}

// Get a temporary URL for previewing or downloading a file
export async function getMediaUrl(mediaId, download = false) {
  const response = await api.get(
    `${MEDIA_BASE}/api/media/${encodeURIComponent(mediaId)}/url`,
    {
      params: { download },
    }
  )

  return response.data
}

// Upload media (admin only)
export async function uploadMedia(file) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await api.post(
    `${MEDIA_BASE}/api/media/upload`,
    formData,
    {
      headers: {
        'Content-Type': undefined,
      },
    }
  )

  return response.data
}

export async function getPowerPointPreview(mediaId) {
  const response = await api.get(
    `${MEDIA_BASE}/api/media/${encodeURIComponent(mediaId)}/preview`,
    { responseType: 'blob' }
  )

  return URL.createObjectURL(response.data)
}

export async function getMediaThumbnail(mediaId) {
  const response = await api.get(
    `${MEDIA_BASE}/api/media/${encodeURIComponent(mediaId)}/thumbnail`,
    { responseType: 'blob' }
  )

  return URL.createObjectURL(response.data)
}