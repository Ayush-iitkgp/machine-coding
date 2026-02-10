import { useRef, useEffect } from 'react'

export type Message = { role: 'user' | 'assistant'; content: string }

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  return (
    <div
      className={`max-w-[85%] rounded-xl px-4 py-3 leading-relaxed ${
        isUser
          ? 'self-end bg-indigo-500 text-white'
          : 'self-start border border-white/10 bg-white/5'
      }`}
    >
      <div className="whitespace-pre-wrap break-words">{message.content}</div>
    </div>
  )
}

export function ChatMessages({
  messages,
  loading,
}: {
  messages: Message[]
  loading: boolean
}) {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  return (
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-4 sm:p-6">
      {messages.length === 0 && !loading && (
        <p className="text-center text-white/50 sm:py-8">Send a message to start the chat.</p>
      )}
      {messages.map((msg, i) => (
        <MessageBubble key={i} message={msg} />
      ))}
      {loading && (
        <div className="max-w-[85%] self-start rounded-xl border border-white/10 bg-white/5 px-4 py-3 opacity-70">
          <div>...</div>
        </div>
      )}
      <div ref={endRef} />
    </div>
  )
}
