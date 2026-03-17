import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../services/api'

export const useArchivesStore = defineStore('archives', () => {
  const archives = ref([])
  const categories = ref([])
  const ages = ref([])
  const loading = ref(false)
  const loadingMore = ref(false)
  const error = ref(null)
  const total = ref(0)
  const PAGE_SIZE = 10

  // Current filter state for loadMore
  const _currentFilters = ref({})

  async function fetchArchives(params = {}) {
    loading.value = true
    error.value = null
    _currentFilters.value = params
    try {
      const response = await api.get('/api/archives', {
        params: { ...params, limit: PAGE_SIZE, offset: 0 },
      })
      archives.value = response.data.items
      total.value = response.data.total
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  const hasMore = () => archives.value.length < total.value

  async function loadMore() {
    if (loadingMore.value || !hasMore()) return
    loadingMore.value = true
    try {
      const response = await api.get('/api/archives', {
        params: { ..._currentFilters.value, limit: PAGE_SIZE, offset: archives.value.length },
      })
      archives.value.push(...response.data.items)
      total.value = response.data.total
    } catch (e) {
      error.value = e.message
    } finally {
      loadingMore.value = false
    }
  }

  async function fetchCategories() {
    try {
      const response = await api.get('/api/categories')
      categories.value = response.data
    } catch (e) {
      error.value = e.message
    }
  }

  async function fetchAges() {
    try {
      const response = await api.get('/api/ages')
      ages.value = response.data
    } catch (e) {
      error.value = e.message
    }
  }

  async function createArchive(formData, { onUploadProgress } = {}) {
    const response = await api.post('/api/archives', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 0,
      onUploadProgress,
    })
    archives.value.unshift(response.data)
    total.value++
    return response.data
  }

  async function updateArchive(id, formData, { onUploadProgress } = {}) {
    const response = await api.put(`/api/archives/${id}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 0,
      onUploadProgress,
    })
    const index = archives.value.findIndex(a => a.id === id)
    if (index !== -1) {
      archives.value[index] = response.data
    }
    return response.data
  }

  async function deleteArchive(id) {
    await api.delete(`/api/archives/${id}`)
    archives.value = archives.value.filter(a => a.id !== id)
    total.value--
  }

  async function publishToDiscord(archiveId) {
    try {
      const response = await api.post('/api/discord/publish', { archive_id: archiveId }, { timeout: 60000 })
      if (response.data.success) {
        const index = archives.value.findIndex(a => a.id === archiveId)
        if (index !== -1) {
          archives.value[index].discord_post_id = response.data.post_id
        }
      }
      return response.data
    } catch (e) {
      console.error('[Discord] Publish error:', e)
      throw e
    }
  }

  async function generateShareLink(archiveId) {
    const response = await api.post('/api/download/token', {
      archive_id: archiveId,
      expiry_seconds: 2592000,
      reusable: true,
    })
    return response.data.download_url
  }

  async function createCategory(data) {
    const response = await api.post('/api/categories', data)
    categories.value.push(response.data)
    return response.data
  }

  async function deleteCategory(id) {
    await api.delete(`/api/categories/${id}`)
    categories.value = categories.value.filter(c => c.id !== id)
  }

  async function createAge(data) {
    const response = await api.post('/api/ages', data)
    ages.value.push(response.data)
    return response.data
  }

  async function deleteAge(id) {
    await api.delete(`/api/ages/${id}`)
    ages.value = ages.value.filter(a => a.id !== id)
  }

  // Archive Editor methods
  async function fetchArchiveContent(id) {
    const response = await api.get(`/api/archives/${id}/content`)
    return response.data
  }

  async function updateChapters(id, chapters) {
    const response = await api.put(`/api/archives/${id}/chapters`, { chapters })
    const index = archives.value.findIndex(a => a.id === id)
    if (index !== -1) {
      archives.value[index] = response.data
    }
    return response.data
  }

  async function updateArchiveCover(id, formData) {
    const response = await api.put(`/api/archives/${id}/archive-cover`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    const index = archives.value.findIndex(a => a.id === id)
    if (index !== -1) {
      archives.value[index] = response.data
    }
    return response.data
  }

  function getChapterIconUrl(archiveId, chapterKey) {
    return `/api/archives/${archiveId}/chapters/${chapterKey}/icon`
  }

  async function updateChapterIcon(archiveId, chapterKey, formData) {
    const response = await api.put(
      `/api/archives/${archiveId}/chapters/${chapterKey}/icon`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
    return response.data
  }

  async function getWaveform(archiveId, chapterKey, samples = 800) {
    const response = await api.get(
      `/api/archives/${archiveId}/chapters/${chapterKey}/waveform`,
      { params: { samples } }
    )
    return response.data
  }

  function getChapterAudioUrl(archiveId, chapterKey) {
    return `/api/archives/${archiveId}/chapters/${chapterKey}/audio`
  }

  async function splitChapter(archiveId, chapterKey, splitPoints) {
    const response = await api.post(
      `/api/archives/${archiveId}/chapters/${chapterKey}/split`,
      { split_points: splitPoints }
    )
    const index = archives.value.findIndex(a => a.id === archiveId)
    if (index !== -1) {
      archives.value[index] = response.data
    }
    return response.data
  }

  async function trimChapter(archiveId, chapterKey, startMs, endMs, mode = 'keep') {
    const response = await api.post(
      `/api/archives/${archiveId}/chapters/${chapterKey}/trim`,
      { start_ms: startMs, end_ms: endMs, mode }
    )
    const index = archives.value.findIndex(a => a.id === archiveId)
    if (index !== -1) {
      archives.value[index] = response.data
    }
    return response.data
  }

  async function mergeChapters(archiveId, chapterKeys, newTitle) {
    const response = await api.post(
      `/api/archives/${archiveId}/chapters/merge`,
      { chapter_keys: chapterKeys, new_title: newTitle }
    )
    const index = archives.value.findIndex(a => a.id === archiveId)
    if (index !== -1) {
      archives.value[index] = response.data
    }
    return response.data
  }

  async function addChapter(archiveId, formData) {
    const response = await api.post(
      `/api/archives/${archiveId}/chapters/add`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 0,
      }
    )
    const index = archives.value.findIndex(a => a.id === archiveId)
    if (index !== -1) {
      archives.value[index] = response.data
    }
    return response.data
  }

  async function replaceChapterAudio(archiveId, chapterKey, formData) {
    const response = await api.put(
      `/api/archives/${archiveId}/chapters/${chapterKey}/audio`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 0,
      }
    )
    const index = archives.value.findIndex(a => a.id === archiveId)
    if (index !== -1) {
      archives.value[index] = response.data
    }
    return response.data
  }

  async function getNfo(archiveId) {
    const response = await api.get(`/api/archives/${archiveId}/nfo`)
    return response.data.content
  }

  async function updateNfo(archiveId, content) {
    const response = await api.put(`/api/archives/${archiveId}/nfo`, { content })
    return response.data
  }

  return {
    archives,
    categories,
    ages,
    loading,
    loadingMore,
    error,
    total,
    hasMore,
    fetchArchives,
    loadMore,
    fetchCategories,
    fetchAges,
    createArchive,
    updateArchive,
    deleteArchive,
    publishToDiscord,
    generateShareLink,
    createCategory,
    deleteCategory,
    createAge,
    deleteAge,
    // Archive Editor
    fetchArchiveContent,
    updateChapters,
    updateArchiveCover,
    getChapterIconUrl,
    updateChapterIcon,
    getWaveform,
    getChapterAudioUrl,
    splitChapter,
    trimChapter,
    mergeChapters,
    addChapter,
    replaceChapterAudio,
    getNfo,
    updateNfo,
  }
})
