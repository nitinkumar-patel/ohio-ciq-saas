import { render } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

const useAuthStatusMock = vi.fn()
vi.mock('./auth/useAuthStatus', () => ({
  useAuthStatus: () => useAuthStatusMock(),
}))

// The unauthenticated branch redirects via window.location and sessionStorage
// -- stub both so jsdom doesn't error, and so we can assert nothing rendered
// before that redirect fires.
vi.mock('./auth/hostedUI', () => ({
  hasAuthorizationCode: () => false,
  consumeLoggedOutHop: () => false,
  redirectToHostedUILogout: vi.fn(),
}))
vi.mock('aws-amplify/auth', () => ({
  signInWithRedirect: vi.fn(),
}))

describe('App', () => {
  beforeEach(() => {
    useAuthStatusMock.mockReset()
  })

  it('renders nothing while the auth check is pending (AC-2)', () => {
    useAuthStatusMock.mockReturnValue({ status: 'pending' })
    const { container } = render(<App />)
    expect(container.innerHTML).toBe('')
  })

  it('renders nothing for an unauthenticated user, before the redirect fires (AC-2)', () => {
    useAuthStatusMock.mockReturnValue({ status: 'unauthenticated' })
    const { container } = render(<App />)
    expect(container.innerHTML).toBe('')
  })
})
