import { useCallback, useEffect, useRef, useState } from 'react'

import { fetchHealth } from '../api/client'

const POLL_INTERVAL_MS = 30000

export const HEALTH_STATES = {
  checking: { label: 'Checking status', tone: 'neutral' },
  operational: { label: 'System operational', tone: 'success' },
  unavailable: { label: 'Backend unavailable', tone: 'error' },
}

/**
 * Poll GET /health and expose one of the HEALTH_STATES keys.
 *
 * Only the two user-facing phrases from the product spec are shown. A
 * reachable API that is not fully healthy is treated as unavailable so the
 * status line never names databases or other internals.
 */
export function useHealth() {
  const [state, setState] = useState('checking')
  const controllerRef = useRef(null)

  const check = useCallback(async () => {
    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller

    try {
      const health = await fetchHealth({ signal: controller.signal })
      setState(health?.status === 'ok' ? 'operational' : 'unavailable')
    } catch (error) {
      if (error?.name !== 'AbortError') {
        setState('unavailable')
      }
    }
  }, [])

  useEffect(() => {
    check()
    const timer = window.setInterval(check, POLL_INTERVAL_MS)

    return () => {
      window.clearInterval(timer)
      controllerRef.current?.abort()
    }
  }, [check])

  return { state, descriptor: HEALTH_STATES[state], refresh: check }
}
