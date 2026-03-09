<template>
  <div class="cover-cropper">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-semibold text-gray-900">Couverture de l'archive</h3>
    </div>

    <div class="grid md:grid-cols-2 gap-6">
      <!-- Upload/Crop area -->
      <div>
        <div
          v-if="!imageUrl"
          class="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 transition-colors cursor-pointer"
          @click="triggerUpload"
          @dragover.prevent
          @drop.prevent="handleDrop"
        >
          <svg class="w-12 h-12 mx-auto text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <p class="text-gray-600 mb-2">Glissez-déposez une image ou cliquez pour sélectionner</p>
          <p class="text-sm text-gray-500">La couverture sera recadrée au ratio 3:4</p>
        </div>

        <div v-else class="space-y-4">
          <div class="cropper-wrapper bg-gray-100 rounded-lg overflow-hidden" style="height: 400px;">
            <Cropper
              ref="cropperRef"
              :src="imageUrl"
              :stencil-props="{
                aspectRatio: 638/1011,
                movable: true,
                resizable: true
              }"
              :default-size="defaultSize"
              class="h-full"
              @change="onCropChange"
            />
          </div>

          <div class="flex gap-2">
            <button
              @click="resetImage"
              class="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Changer d'image
            </button>
            <div class="flex-1"></div>
            <button
              @click="saveCover"
              :disabled="saving"
              class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {{ saving ? 'Enregistrement...' : 'Enregistrer la couverture' }}
            </button>
          </div>
        </div>

        <input
          type="file"
          accept="image/*"
          @change="handleFileSelect"
          class="hidden"
          ref="fileInput"
        />
      </div>

      <!-- Preview -->
      <div>
        <h4 class="text-sm font-medium text-gray-700 mb-3">Aperçu</h4>
        <div class="bg-gray-100 rounded-lg p-4 flex items-center justify-center" style="min-height: 300px;">
          <div
            v-if="previewUrl"
            class="shadow-lg rounded-lg overflow-hidden"
            style="width: 160px; height: 254px;"
          >
            <img :src="previewUrl" class="w-full h-full object-cover" />
          </div>
          <div v-else class="text-center text-gray-500">
            <svg class="w-16 h-16 mx-auto mb-2 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            <p class="text-sm">Sélectionnez une image<br/>pour voir l'aperçu</p>
          </div>
        </div>

        <!-- Current cover info -->
        <div v-if="currentCoverUrl" class="mt-4 p-3 bg-gray-50 rounded-lg">
          <p class="text-sm text-gray-600 mb-2">Couverture actuelle :</p>
          <img :src="currentCoverUrl" class="w-20 h-auto rounded shadow" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Cropper } from 'vue-advanced-cropper'
import 'vue-advanced-cropper/dist/style.css'
import { useArchivesStore } from '../../stores/archives'

const props = defineProps({
  archiveId: { type: Number, required: true },
  currentCoverPath: { type: String, default: null }
})

const emit = defineEmits(['saved'])

const store = useArchivesStore()
const fileInput = ref(null)
const cropperRef = ref(null)
const imageUrl = ref(null)
const imageFile = ref(null)
const previewUrl = ref(null)
const cropData = ref(null)
const saving = ref(false)

const currentCoverUrl = computed(() => {
  if (!props.currentCoverPath) return null
  return `/api/archives/cover/${props.currentCoverPath}`
})

function defaultSize({ imageSize }) {
  // Default to center crop with Yoto card aspect (638:1011)
  const targetRatio = 638 / 1011
  const imageRatio = imageSize.width / imageSize.height

  let width, height
  if (imageRatio > targetRatio) {
    height = imageSize.height
    width = height * targetRatio
  } else {
    width = imageSize.width
    height = width / targetRatio
  }

  return {
    width,
    height
  }
}

function triggerUpload() {
  fileInput.value?.click()
}

function handleFileSelect(event) {
  const file = event.target.files?.[0]
  if (file) {
    loadImage(file)
  }
}

function handleDrop(event) {
  const file = event.dataTransfer.files?.[0]
  if (file && file.type.startsWith('image/')) {
    loadImage(file)
  }
}

function loadImage(file) {
  imageFile.value = file
  imageUrl.value = URL.createObjectURL(file)
  previewUrl.value = null
  cropData.value = null
}

function resetImage() {
  if (imageUrl.value) {
    URL.revokeObjectURL(imageUrl.value)
  }
  imageUrl.value = null
  imageFile.value = null
  previewUrl.value = null
  cropData.value = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

function onCropChange({ coordinates, canvas }) {
  cropData.value = {
    x: Math.round(coordinates.left),
    y: Math.round(coordinates.top),
    width: Math.round(coordinates.width),
    height: Math.round(coordinates.height)
  }

  // Generate preview
  if (canvas) {
    previewUrl.value = canvas.toDataURL('image/jpeg', 0.9)
  }
}

async function saveCover() {
  if (!imageFile.value || !cropData.value) return

  saving.value = true
  try {
    const formData = new FormData()
    formData.append('cover_file', imageFile.value)
    formData.append('crop_x', cropData.value.x)
    formData.append('crop_y', cropData.value.y)
    formData.append('crop_width', cropData.value.width)
    formData.append('crop_height', cropData.value.height)

    await store.updateArchiveCover(props.archiveId, formData)
    emit('saved')
    resetImage()
  } catch (e) {
    console.error('Save cover failed:', e)
    alert('Erreur lors de l\'enregistrement: ' + e.message)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.cropper-wrapper :deep(.vue-advanced-cropper) {
  background: #f3f4f6;
}
</style>
