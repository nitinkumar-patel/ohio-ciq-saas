import { fetchAuthSession } from 'aws-amplify/auth'

export type ChatResult =
  | { ok: true; reply: string }
  | { ok: false; status: number; message: string }

export async function sendChatMessage(message: string): Promise<ChatResult> {
  try {
    const session = await fetchAuthSession()
    const idToken = session.tokens?.idToken?.toString()
    if (!idToken) {
      return { ok: false, status: 401, message: 'No active session.' }
    }

    const apiUrl = import.meta.env.VITE_API_URL as string
    const response = await fetch(`${apiUrl}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${idToken}`,
      },
      body: JSON.stringify({ message }),
    })

    let body: { message?: string; reply?: string } = {}
    try {
      body = await response.json()
    } catch {
      // non-JSON body (e.g. a gateway/network error page) -- fall through
      // with an empty body so the generic error message below applies.
    }

    if (!response.ok) {
      return { ok: false, status: response.status, message: body.message ?? 'Request failed.' }
    }
    return { ok: true, reply: body.reply ?? '' }
  } catch (err) {
    // Network failure, DNS/CORS rejection, or an auth-session error -- never
    // let this escape as an unhandled rejection and wedge the chat UI.
    const message = err instanceof Error ? err.message : 'Request failed.'
    return { ok: false, status: 0, message }
  }
}
