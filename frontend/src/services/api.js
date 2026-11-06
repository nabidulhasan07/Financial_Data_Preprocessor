import axios from 'axios'

const api = axios.create({
  // Relative by default so local Vite proxy and same-origin production work.
  // Set VITE_API_BASE_URL only when the API is hosted on a separate origin.
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 5000,
})

export async function getHealth(signal) {
  const response = await api.get('/health', { signal })
  return response.data
}

export async function uploadDataset(file) {
  const form = new FormData()
  form.append('file', file)
  const response = await api.post('/datasets', form, { timeout: 60000 })
  return response.data
}

export async function cleanDataset(datasetId, options) {
  const response = await api.post(`/datasets/${datasetId}/clean`, options, { timeout: 60000 })
  return response.data
}

export async function getValidation(datasetId) {
  const response = await api.get(`/datasets/${datasetId}/validation`)
  return response.data
}

export async function getAnalysis(datasetId) {
  const response = await api.get(`/datasets/${datasetId}/analysis`)
  return response.data
}

export async function getQualityReport(datasetId) {
  const response = await api.get(`/datasets/${datasetId}/quality`)
  return response.data
}

export async function downloadDataset(datasetId, format) {
  const response = await api.get(`/datasets/${datasetId}/export`, { params: { format }, responseType: 'blob' })
  return response.data
}

export function getApiError(error) {
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (error.code === 'ECONNABORTED') return 'The request took too long. Try a smaller file or try again.'
  if (!error.response) return 'Could not reach the backend. Make sure the FastAPI server is running.'
  return 'Something went wrong while processing this dataset. Please check the file and try again.'
}
