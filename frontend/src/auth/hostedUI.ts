// Cognito's Hosted UI keeps its own SSO session cookie (~1 hour) independent
// of this app's in-memory token store. Closing and reopening the tab clears
// the app's tokens but not that cookie, so a plain redirect to /authorize
// would silently complete the existing session -- defeating AC-12. Routing
// through /logout first clears the cookie, guaranteeing a fresh credential
// prompt. Both callback_urls and logout_urls are registered as the same
// exact URL (see infra/terraform/cognito.tf), so this flag is what tells
// the two return paths apart -- not a token or transcript, so AC-11's
// storage check is unaffected, and it is removed the instant it is read.
const LOGGED_OUT_HOP_KEY = 'chatbot.loggedOutHop'
const REDIRECT_PATH = '/callback'

function redirectUri(): string {
  return `${window.location.origin}${REDIRECT_PATH}`
}

export function hasAuthorizationCode(): boolean {
  return new URLSearchParams(window.location.search).has('code')
}

export function consumeLoggedOutHop(): boolean {
  const had = sessionStorage.getItem(LOGGED_OUT_HOP_KEY) === '1'
  sessionStorage.removeItem(LOGGED_OUT_HOP_KEY)
  return had
}

export function redirectToHostedUILogout(): void {
  sessionStorage.setItem(LOGGED_OUT_HOP_KEY, '1')
  const domain = import.meta.env.VITE_COGNITO_DOMAIN as string
  const clientId = import.meta.env.VITE_COGNITO_CLIENT_ID as string
  const url =
    `https://${domain}/logout?client_id=${encodeURIComponent(clientId)}` +
    `&logout_uri=${encodeURIComponent(redirectUri())}`
  window.location.assign(url)
}
