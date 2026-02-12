import { useRef, useState, type ChangeEvent } from 'react'
import { ChatInput } from './chat-input'
import { ChatMessages, type Message } from './chat-messages'
import { chatMessageSchema } from '../../lib/validation'

type ChatApiError = { detail?: string | { msg?: string }[] }

type RetrievedChunk = {
  id: number
  document_id: string
  document_name?: string | null
  section: string
  content: string
}

type ChatApiResponse = {
  response: string
  document_id?: string | null
  retrieved_chunks?: RetrievedChunk[]
}

type UploadResponse = {
  document_id: string
  chunks: number
}

async function deleteDocument(documentId: string): Promise<void> {
  const res = await fetch(`/documents/${documentId}`, { method: 'DELETE' })
  if (!res.ok && res.status !== 404) {
    throw new Error('Failed to delete document')
  }
}

async function uploadDocument(file: File): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const res = await fetch('/documents/upload', {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) {
    const data = (await res.json().catch(() => ({}))) as { detail?: string }
    throw new Error(data.detail ?? 'Failed to upload document')
  }

  return (await res.json()) as UploadResponse
}

async function sendChatMessage(
  message: string,
  options?: {
    documentId?: string | null
    history?: { role: 'user' | 'assistant'; content: string }[]
  },
): Promise<ChatApiResponse> {
  const res = await fetch('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      document_id: options?.documentId ?? undefined,
      history: options?.history ?? undefined,
    }),
  })
  const data = (await res.json()) as ChatApiError | ChatApiResponse

  if (!res.ok) {
    const errorData = data as ChatApiError
    const detail = errorData.detail

    const errMsg =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail
              .map((d: { msg?: string }) => (d && d.msg ? d.msg : ''))
              .join(', ')
          : 'Failed to get response'
    throw new Error(errMsg)
  }

  return data as ChatApiResponse
}

export function ChatApp() {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null)
  const [documentId, setDocumentId] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  function handleUploadClick() {
    fileInputRef.current?.click()
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (file) {
      void (async () => {
        try {
          setUploading(true)
          if (documentId) {
            await deleteDocument(documentId)
          }
          const uploaded = await uploadDocument(file)
          setDocumentId(uploaded.document_id)
          setSelectedFileName(file.name)
        } catch (err) {
          setSelectedFileName(null)
          setDocumentId(null)
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              content: `Error uploading document: ${
                err instanceof Error ? err.message : 'Unknown error'
              }`,
            },
          ])
        } finally {
          setUploading(false)
        }
      })()
    }
  }

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
      const history = messages.map((m) => ({ role: m.role, content: m.content }))
      const { response, retrieved_chunks, document_id } = await sendChatMessage(text, {
        documentId,
        history,
      })
      if (document_id) {
        setDocumentId(document_id)
      }

      const isLlmError =
        response.startsWith('Unable to process the question at present') ||
        response.startsWith('[LLM_ERROR]')

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response,
          // Do not show retrieved chunks when the LLM returned an error message.
          retrievedChunks: isLlmError ? undefined : retrieved_chunks,
        },
      ])
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
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h1 className="m-0 text-xl font-semibold sm:text-2xl">Odin AI Chat</h1>
          <div className="flex flex-col items-start gap-2 text-xs text-white/70 sm:flex-row sm:items-center sm:gap-4">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleUploadClick}
                className="rounded-lg border border-white/20 bg-white/5 px-3 py-2 text-xs font-medium text-white hover:border-indigo-400 hover:bg-indigo-500/20"
              >
                Upload document
              </button>
            </div>
            {selectedFileName && (
              <span className="max-w-[180px] truncate text-white/70" title={selectedFileName}>
                Selected: {selectedFileName}
              </span>
            )}
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              onChange={handleFileChange}
              accept=".pdf,.txt,.doc,.docx"
            />
          </div>
        </div>
      </header>

      {uploading && (
        <div className="flex-shrink-0 border-b border-amber-500/30 bg-amber-500/10 px-4 py-2 text-xs text-amber-200 sm:px-6">
          Parsing uploaded document, please wait…
        </div>
      )}

      <ChatMessages messages={messages} loading={loading} />

      <ChatInput onSubmit={handleSubmit} disabled={loading || uploading} />
    </div>
  )
}
