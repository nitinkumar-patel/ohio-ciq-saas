import { fetchAuthSession } from 'aws-amplify/auth'
import { Hub } from 'aws-amplify/utils'
import { useEffect, useState } from 'react'

export type AuthStatus =
  | { status: 'pending' }
  | { status: 'authenticated' }
  | { status: 'unauthenticated' }

export function useAuthStatus(): AuthStatus {
  const [state, setState] = useState<AuthStatus>({ status: 'pending' })

  useEffect(() => {
    let cancelled = false

    const check = async () => {
      try {
        const session = await fetchAuthSession()
        if (cancelled) return
        setState(
          session.tokens?.idToken
            ? { status: 'authenticated' }
            : { status: 'unauthenticated' },
        )
      } catch (err) {
        // Most commonly a stale/missing frontend/.env.local after a
        // terraform destroy+apply recreate (see frontend/README.md) --
        // logged so that failure mode isn't a silent blank page.
        console.error('useAuthStatus: fetchAuthSession failed', err)
        if (!cancelled) setState({ status: 'unauthenticated' })
      }
    }

    void check()

    const unsubscribe = Hub.listen('auth', ({ payload }) => {
      if (payload.event === 'signInWithRedirect') void check()
      if (payload.event === 'signInWithRedirect_failure') {
        // The authorization code was already consumed (single-use) or
        // rejected -- clear it from the URL so the unauthenticated redirect
        // effect re-fires instead of finding a stale `code` param forever
        // and rendering a permanently blank page.
        window.history.replaceState({}, '', window.location.pathname)
        setState({ status: 'unauthenticated' })
      }
    })

    return () => {
      cancelled = true
      unsubscribe()
    }
  }, [])

  return state
}
