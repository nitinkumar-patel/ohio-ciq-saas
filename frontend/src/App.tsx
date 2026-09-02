import { signInWithRedirect } from 'aws-amplify/auth'
import { useEffect } from 'react'
import './auth/config'
import {
  consumeLoggedOutHop,
  hasAuthorizationCode,
  redirectToHostedUILogout,
} from './auth/hostedUI'
import { useAuthStatus } from './auth/useAuthStatus'
import { ChatScreen } from './chat/ChatScreen'

function App() {
  const auth = useAuthStatus()

  useEffect(() => {
    if (auth.status !== 'unauthenticated') return
    if (hasAuthorizationCode()) return // Amplify's Hub is processing it

    if (consumeLoggedOutHop()) {
      void signInWithRedirect()
    } else {
      redirectToHostedUILogout()
    }
  }, [auth.status])

  // AC-2: nothing renders -- not even a loading placeholder -- until the
  // auth check resolves to 'authenticated'.
  if (auth.status !== 'authenticated') {
    return null
  }

  return <ChatScreen />
}

export default App
