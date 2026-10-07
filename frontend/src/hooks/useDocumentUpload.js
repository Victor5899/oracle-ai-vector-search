import { useCallback, useState } from 'react'

import { uploadDocument } from '../api/client'

const ACCEPTED_EXTENSIONS = ['.pdf', '.txt']
const MAX_FILE_BYTES = 25 * 1024 * 1024

function extensionOf(name) {
  const dot = name.lastIndexOf('.')
  return dot === -1 ? '' : name.slice(dot).toLowerCase()
}

/** Catch the obvious problems locally so the file is never sent in vain. */
function validate(file) {
  if (!ACCEPTED_EXTENSIONS.includes(extensionOf(file.name))) {
    return 'Only PDF and TXT files can be processed. Choose a different file.'
  }

  if (file.size === 0) {
    return 'That file is empty. Choose a file that contains text.'
  }

  if (file.size > MAX_FILE_BYTES) {
    return 'That file is larger than 25 MB. Choose a smaller document.'
  }

  return null
}

/**
 * Run one upload at a time and keep the documents ingested in this session.
 *
 * `phase` moves through idle, uploading, processing, done and error. The
 * processing phase begins once the browser has finished the transfer, while
 * the server is still chunking and embedding.
 */
export function useDocumentUpload() {
  const [documents, setDocuments] = useState([])
  const [phase, setPhase] = useState('idle')
  const [progress, setProgress] = useState(0)
  const [fileName, setFileName] = useState('')
  const [error, setError] = useState(null)

  const reset = useCallback(() => {
    setPhase('idle')
    setProgress(0)
    setFileName('')
    setError(null)
  }, [])

  const upload = useCallback(async (file) => {
    if (!file) {
      return
    }

    setFileName(file.name)
    setError(null)
    setProgress(0)

    const problem = validate(file)

    if (problem) {
      setPhase('error')
      setError(problem)
      return
    }

    setPhase('uploading')

    try {
      const result = await uploadDocument(file, {
        onProgress: setProgress,
        onTransferComplete: () => setPhase('processing'),
      })

      setDocuments((current) => [
        {
          key: `${result.document_id}-${Date.now()}`,
          documentId: result.document_id,
          fileName: result.file_name,
          chunks: result.number_of_chunks,
          embeddings: result.number_of_embeddings,
          status: result.status,
        },
        ...current.filter((document) => document.documentId !== result.document_id),
      ])
      setPhase('done')
    } catch (requestError) {
      setPhase('error')
      setError(requestError?.message ?? 'The document could not be processed.')
    }
  }, [])

  const isBusy = phase === 'uploading' || phase === 'processing'

  return { documents, phase, progress, fileName, error, isBusy, upload, reset }
}

export { ACCEPTED_EXTENSIONS }
