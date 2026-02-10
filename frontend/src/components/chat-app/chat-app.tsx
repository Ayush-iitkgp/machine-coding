import { useState } from 'react'
import { ChatInput } from './chat-input'
import { ChatMessages, type Message } from './chat-messages'
import { chatMessageSchema } from '../../lib/validation'

async function sendChatMessage(message: string): Promise<string> {
  const res = await fetch('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  })
  const data = (await res.json()) as { detail?: string | { msg?: string }[] }

  if (!res.ok) {
    const errMsg =
      typeof data?.detail === 'string'
        ? data.detail
        : Array.isArray(data?.detail)
          ? data.detail.map((d) => (typeof d === 'object' && d && 'msg' in d ? d.msg : '')).join(', ')
          : 'Failed to get response'
    throw new Error(errMsg)
  }

  return (data as { response: string }).response
}

export function ChatApp() {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)

  async function handleSubmit(message: string): Promise<void> {
    const parsed = chatMessageSchema.safeParse(message)
    if (!parsed.success) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Validation: ${parsed.error.errors[0]?.message ?? 'Invalid input'}`,
        },
      ])
      return
    }

    const text = parsed.data
    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setLoading(true)

    try {
      const response = await sendChatMessage(text)
      setMessages((prev) => [...prev, { role: 'assistant', content: response }])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Error: ${err instanceof Error ? err.message : 'Unknown error'}` },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto flex h-dvh max-h-screen max-w-3xl flex-col bg-slate-900 text-white sm:max-w-3xl">
      <header className="flex-shrink-0 border-b border-white/10 px-4 py-4 sm:px-6">
        <h1 className="m-0 text-xl font-semibold sm:text-2xl">Odin AI Chat</h1>
      </header>

      <ChatMessages messages={messages} loading={loading} />

      <ChatInput onSubmit={handleSubmit} />
    </div>
  )
}
