import { Amplify } from 'aws-amplify'
import { cognitoUserPoolsTokenProvider } from 'aws-amplify/auth/cognito'
import { inMemoryTokenStorage } from './tokenStorage'

const required = {
  VITE_COGNITO_USER_POOL_ID: import.meta.env.VITE_COGNITO_USER_POOL_ID,
  VITE_COGNITO_CLIENT_ID: import.meta.env.VITE_COGNITO_CLIENT_ID,
  VITE_COGNITO_DOMAIN: import.meta.env.VITE_COGNITO_DOMAIN,
  VITE_API_URL: import.meta.env.VITE_API_URL,
}
const missing = Object.entries(required)
  .filter(([, value]) => !value)
  .map(([key]) => key)
if (missing.length > 0) {
  throw new Error(
    `Missing required env var(s): ${missing.join(', ')}. ` +
      'Regenerate frontend/.env.local from `terraform output` -- see frontend/README.md.',
  )
}

Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID,
      userPoolClientId: import.meta.env.VITE_COGNITO_CLIENT_ID,
      loginWith: {
        oauth: {
          domain: import.meta.env.VITE_COGNITO_DOMAIN,
          scopes: ['openid', 'email'],
          redirectSignIn: [`${window.location.origin}/callback`],
          redirectSignOut: [`${window.location.origin}/callback`],
          responseType: 'code',
        },
      },
    },
  },
})

// AC-11: override Amplify's localStorage default with an in-memory store.
cognitoUserPoolsTokenProvider.setKeyValueStorage(inMemoryTokenStorage)
