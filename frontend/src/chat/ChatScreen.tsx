import { signOut } from 'aws-amplify/auth'
import { useState } from 'react'
import { sendChatMessage } from './api'

type Message = { author: 'user' | 'bot'; text: string }

export function ChatScreen() {
  const [messages, setMessages] = useState<Message[]>([])
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)

  const handleSend = async () => {
    const text = draft.trim()
    if (!text || sending) return

    setMessages((prev) => [...prev, { author: 'user', text }])
    setDraft('')
    setSending(true)

    try {
      const result = await sendChatMessage(text)
      if (result.ok) {
        setMessages((prev) => [...prev, { author: 'bot', text: result.reply }])
      } else if (result.status === 401) {
        // Session is no longer valid -- clear it and force a fresh login
        // rather than showing a broken chat state.
        await signOut()
      } else {
        setMessages((prev) => [...prev, { author: 'bot', text: `Error: ${result.message}` }])
      }
    } finally {
      // Always release the Send button, even if signOut() or an unexpected
      // rejection reaches here -- a permanently disabled Send button with no
      // visible error is worse than an occasional extra click.
      setSending(false)
    }
  }

  return (
    <div>
      <header>
        <button type="button" onClick={() => void signOut()}>
          Sign out
        </button>
      </header>
      <ul>
        {messages.map((m, i) => (
          <li key={i}>
            <strong>{m.author === 'user' ? 'You' : 'Bot'}:</strong> {m.text}
          </li>
        ))}
      </ul>
      <input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') void handleSend()
        }}
        placeholder="Type a message"
      />
      <button type="button" onClick={() => void handleSend()} disabled={sending}>
        Send
      </button>
    </div>
  )
}
