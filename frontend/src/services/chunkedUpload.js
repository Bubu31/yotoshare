import axios from 'axios'

const CHUNK_SIZE = 5 * 1024 * 1024 // 5 MB

/**
 * Initiate a chunked upload session
 * @param {string} filename
 * @param {number} fileSize
 * @param {Object} metadata - additional fields (pseudonym, parent_submission_id, etc)
 * @returns {Promise<string>} uploadId
 */
export async function initChunkedUpload(filename, fileSize, metadata = {}) {
  const form = new FormData()
  form.append('filename', filename)
  form.append('total_size', fileSize)
  form.append('total_chunks', Math.ceil(fileSize / CHUNK_SIZE))
  form.append('chunk_size', CHUNK_SIZE)

  for (const [key, value] of Object.entries(metadata)) {
    if (value !== null && value !== undefined) {
      form.append(key, value)
    }
  }

  const response = await axios.post('/api/uploads/init', form)
  return response.data.upload_id
}

/**
 * Upload a single chunk
 * @param {string} uploadId
 * @param {number} chunkIndex
 * @param {Blob} chunkData
 * @returns {Promise}
 */
export async function uploadChunk(uploadId, chunkIndex, chunkData) {
  const form = new FormData()
  form.append('chunk_index', chunkIndex)
  form.append('chunk', chunkData, `chunk_${chunkIndex}`)

  return axios.post(`/api/uploads/${uploadId}/chunk`, form)
}

/**
 * Complete a chunked upload
 * @param {string} uploadId
 * @returns {Promise}
 */
export async function completeChunkedUpload(uploadId) {
  return axios.post(`/api/uploads/${uploadId}/complete`)
}

/**
 * Cancel a chunked upload
 * @param {string} uploadId
 * @returns {Promise}
 */
export async function cancelChunkedUpload(uploadId) {
  try {
    return axios.delete(`/api/uploads/${uploadId}`)
  } catch {
    // Ignore cleanup errors
  }
}

/**
 * Upload a file using chunked upload with custom endpoints
 * Calls onProgress with {uploadedBytes, totalBytes, uploadProgress}
 * @param {File} file
 * @param {Object} metadata - additional fields for init request
 * @param {Function} onProgress - callback for progress updates
 * @param {Object} options - optional config {initEndpoint, chunkEndpoint, completeEndpoint}
 * @returns {Promise}
 */
export async function uploadFileChunked(file, metadata = {}, onProgress = null, options = {}) {
  const initEndpoint = options.initEndpoint || '/api/uploads/init'
  const chunkEndpoint = options.chunkEndpoint || '/api/uploads'
  const completeEndpoint = options.completeEndpoint || '/api/uploads'

  const totalChunks = Math.ceil(file.size / CHUNK_SIZE)
  let uploadId = null

  try {
    // 1. Initialize session
    const form = new FormData()
    form.append('filename', file.name)
    form.append('total_size', file.size)
    form.append('total_chunks', totalChunks)
    form.append('chunk_size', CHUNK_SIZE)

    for (const [key, value] of Object.entries(metadata)) {
      if (value !== null && value !== undefined) {
        form.append(key, value)
      }
    }

    const initResponse = await axios.post(initEndpoint, form)
    uploadId = initResponse.data.upload_id

    let uploadedBytes = 0
    const totalBytes = file.size

    // 2. Upload chunks sequentially
    for (let i = 0; i < totalChunks; i++) {
      const start = i * CHUNK_SIZE
      const end = Math.min(start + CHUNK_SIZE, file.size)
      const chunk = file.slice(start, end)

      const chunkForm = new FormData()
      chunkForm.append('chunk_index', i)
      chunkForm.append('chunk', chunk, `chunk_${i}`)

      await axios.post(`${chunkEndpoint}/${uploadId}/chunk`, chunkForm)

      uploadedBytes = end
      const uploadProgress = Math.round((uploadedBytes / totalBytes) * 95)

      if (onProgress) {
        onProgress({
          uploadedBytes,
          totalBytes,
          uploadProgress,
          chunkIndex: i,
          totalChunks,
        })
      }
    }

    // 3. Finalize upload
    const result = await axios.post(`${completeEndpoint}/${uploadId}/complete`)

    if (onProgress) {
      onProgress({
        uploadedBytes: totalBytes,
        totalBytes,
        uploadProgress: 100,
        chunkIndex: totalChunks,
        totalChunks,
      })
    }

    return result

  } catch (error) {
    // Cleanup on error
    if (uploadId) {
      try {
        const deleteEndpoint = options.completeEndpoint || '/api/uploads'
        await axios.delete(`${deleteEndpoint}/${uploadId}`)
      } catch {
        // Ignore cleanup errors
      }
    }
    throw error
  }
}
