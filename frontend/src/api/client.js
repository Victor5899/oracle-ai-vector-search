/**
 * The only module that talks to the FastAPI backend.
 *
 * Three endpoints are used: GET /health, POST /documents/upload and
 * POST /query. Every failure is turned into an ApiError carrying a message
 * that is safe to render, so components never have to inspect responses.
 */

const configuredBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').trim()

/**
 * Deployed API origin when VITE_API_BASE_URL is set.
 * Blank locally, so requests use /api and the Vite dev proxy.
 */
export const API_BASE_URL = (configuredBaseUrl || '/api').replace(/\/+$/, '')

const NETWORK_MESSAGE =
  'The backend could not be reached. Check that the API is running, then try again.'
const UNEXPECTED_MESSAGE = 'Something went wrong on the server. Please try again.'
const MALFORMED_MESSAGE = 'The server returned an unexpected response.'
const MAX_DETAIL_LENGTH = 240

export class ApiError extends Error {
  constructor(message, { status = 0 } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/** Keep server text out of the interface unless it reads like a message. */
function isPresentable(detail) {
  return (
    typeof detail === 'string' &&
    detail.length > 0 &&
    detail.length <= MAX_DETAIL_LENGTH &&
    !/traceback|file "|line \d+, in |\bat \w+\.\w+\(/i.test(detail)
  )
}

function extractDetail(payload) {
  const detail = payload?.detail

  if (isPresentable(detail)) {
    return detail
  }

  // FastAPI request validation errors arrive as a list of issues.
  if (Array.isArray(detail)) {
    const combined = detail
      .map((issue) => issue?.msg)
      .filter((message) => typeof message === 'string')
      .join('. ')

    if (isPresentable(combined)) {
      return combined
    }
  }

  return ''
}

function parseJson(text) {
  if (!text) {
    return null
  }

  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

function failureMessage(status, text) {
  const detail = extractDetail(parseJson(text))

  if (detail) {
    return detail
  }

  return status >= 500 ? UNEXPECTED_MESSAGE : MALFORMED_MESSAGE
}

async function request(path, { signal, ...options } = {}) {
  let response

  try {
    response = await fetch(`${API_BASE_URL}${path}`, { signal, ...options })
  } catch (error) {
    if (error?.name === 'AbortError') {
      throw error
    }
    throw new ApiError(NETWORK_MESSAGE)
  }

  const text = await response.text()

  if (!response.ok) {
    throw new ApiError(failureMessage(response.status, text), { status: response.status })
  }

  const payload = parseJson(text)

  if (payload === null) {
    throw new ApiError(MALFORMED_MESSAGE, { status: response.status })
  }

  return payload
}

/**
 * Read service liveness.
 *
 * @returns {Promise<{status: string, service: string, database: string}>}
 */
export function fetchHealth({ signal } = {}) {
  return request('/health', {
    method: 'GET',
    headers: { Accept: 'application/json' },
    signal,
  })
}

/**
 * Ask a question about the stored documents.
 *
 * @returns {Promise<{question: string, answer: string, sources: Array<object>}>}
 */
export function askQuestion({ question, topK, signal }) {
  return request('/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ question, top_k: topK }),
    signal,
  })
}

/**
 * Send a PDF or TXT file through the ingestion pipeline.
 *
 * XMLHttpRequest is used instead of fetch because it reports upload progress,
 * which lets the interface separate the transfer from the server-side
 * chunking and embedding work.
 *
 * @param {File} file
 * @param {{onProgress?: (fraction: number) => void, onTransferComplete?: () => void}} handlers
 * @returns {Promise<{document_id: number, file_name: string, number_of_chunks: number,
 *   number_of_embeddings: number, status: string}>}
 */
export function uploadDocument(file, { onProgress, onTransferComplete } = {}) {
  return new Promise((resolve, reject) => {
    const form = new FormData()
    form.append('file', file)

    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${API_BASE_URL}/documents/upload`)
    xhr.setRequestHeader('Accept', 'application/json')

    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable) {
        onProgress?.(event.loaded / event.total)
      }
    })

    xhr.upload.addEventListener('load', () => {
      onProgress?.(1)
      onTransferComplete?.()
    })

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        const payload = parseJson(xhr.responseText)

        if (payload === null) {
          reject(new ApiError(MALFORMED_MESSAGE, { status: xhr.status }))
          return
        }

        resolve(payload)
        return
      }

      reject(new ApiError(failureMessage(xhr.status, xhr.responseText), { status: xhr.status }))
    })

    xhr.addEventListener('error', () => reject(new ApiError(NETWORK_MESSAGE)))
    xhr.addEventListener('timeout', () => reject(new ApiError(NETWORK_MESSAGE)))

    xhr.send(form)
  })
}
