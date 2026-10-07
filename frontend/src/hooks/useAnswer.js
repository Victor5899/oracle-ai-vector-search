import { useCallback, useEffect, useRef, useState } from 'react'

import { askQuestion } from '../api/client'

/**
 * Submit a question to POST /query and hold the resulting answer.
 *
 * `status` is one of idle, loading, ready or error. Only the most recent
 * question is kept: an earlier request in flight is abandoned so a slow
 * answer can never overwrite a newer one.
 */
export function useAnswer() {
  const [status, setStatus] = useState('idle')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const controllerRef = useRef(null)

  useEffect(() => () => controllerRef.current?.abort(), [])

  const ask = useCallback(async (question, topK) => {
    const trimmed = question.trim()

    if (!trimmed) {
      return
    }

    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller

    setStatus('loading')
    setError(null)
    setResult(null)

    try {
      const payload = await askQuestion({ question: trimmed, topK, signal: controller.signal })

      setResult({
        question: payload.question,
        answer: payload.answer,
        sources: Array.isArray(payload.sources) ? payload.sources : [],
      })
      setStatus('ready')
    } catch (requestError) {
      if (requestError?.name === 'AbortError') {
        return
      }

      setError(requestError?.message ?? 'The question could not be answered.')
      setStatus('error')
    }
  }, [])

  const reset = useCallback(() => {
    controllerRef.current?.abort()
    setStatus('idle')
    setResult(null)
    setError(null)
  }, [])

  return { status, result, error, ask, reset }
}
