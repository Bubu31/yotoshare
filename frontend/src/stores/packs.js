import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../services/api'

export const usePacksStore = defineStore('packs', () => {
  const packs = ref([])
  const loading = ref(false)
  const error = ref(null)
  const assets = ref({ background: null, mascot: null })

  async function fetchPacks() {
    loading.value = true
    error.value = null
    try {
      const response = await api.get('/api/packs')
      packs.value = response.data
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  async function createPack(data) {
    const response = await api.post('/api/packs', data)
    packs.value.unshift(response.data)
    return response.data
  }

  async function resharePack(id) {
    const response = await api.post(`/api/packs/${id}/reshare`)
    const index = packs.value.findIndex(p => p.id === id)
    if (index !== -1) {
      packs.value[index] = response.data
    }
    return response.data
  }

  async function deletePack(id) {
    await api.delete(`/api/packs/${id}`)
    packs.value = packs.value.filter(p => p.id !== id)
  }

  async function regenerateImage(id) {
    const response = await api.post(`/api/packs/${id}/regenerate-image`)
    const index = packs.value.findIndex(p => p.id === id)
    if (index !== -1) {
      packs.value[index] = response.data
    }
    return response.data
  }

  async function publishToDiscord(packId) {
    const response = await api.post('/api/discord/publish-pack', { pack_id: packId }, { timeout: 60000 })
    if (response.data.success) {
      const index = packs.value.findIndex(p => p.id === packId)
      if (index !== -1) {
        packs.value[index].discord_post_id = response.data.post_id
      }
    }
    return response.data
  }

  async function fetchAssets() {
    try {
      const response = await api.get('/api/packs/assets')
      assets.value = response.data
    } catch (e) {
      // Silently fail — assets are optional
    }
  }

  async function uploadAsset(type, file) {
    const formData = new FormData()
    formData.append('image', file)
    const response = await api.post(`/api/packs/assets/${type}`, formData)
    assets.value[type] = response.data.filename
    return response.data
  }

  async function deleteAsset(type) {
    await api.delete(`/api/packs/assets/${type}`)
    assets.value[type] = null
  }

  return {
    packs,
    loading,
    error,
    assets,
    fetchPacks,
    createPack,
    resharePack,
    deletePack,
    regenerateImage,
    publishToDiscord,
    fetchAssets,
    uploadAsset,
    deleteAsset,
  }
})
