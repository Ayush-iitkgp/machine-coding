import { useRef } from 'react'
import { useFormStatus } from 'react-dom'

function ChatInputForm({
  onSubmit,
}: {
  onSubmit: (message: string) => Promise<void>
}) {
  const { pending } = useFormStatus()
  const formRef = useRef<HTMLFormElement>(null)

  return (
    <form
      ref={formRef}
      action={async (formData: FormData) => {
        const message = (formData.get('message') as string)?.trim() ?? ''
        if (message) {
          await onSubmit(message)
          formRef.current?.reset()
        }
      }}
      className="flex gap-3 border-t border-white/10 bg-black/20 p-4 sm:p-4"
    >
      <textarea
        name="message"
        placeholder="Type a message..."
        rows={1}
        disabled={pending}
        className="min-h-11 max-h-32 flex-1 resize-none rounded-lg border border-white/20 bg-white/5 px-4 py-3 font-sans text-inherit placeholder:text-white/40 focus:border-indigo-500 focus:outline-none disabled:opacity-50 sm:min-h-11"
      />
      <button
        type="submit"
        disabled={pending}
        className="self-end rounded-lg border-0 bg-indigo-500 px-5 py-3 font-medium text-white hover:bg-indigo-600 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {pending ? '…' : 'Send'}
      </button>
    </form>
  )
}

export function ChatInput({
  onSubmit,
}: {
  onSubmit: (message: string) => Promise<void>
}) {
  return <ChatInputForm onSubmit={onSubmit} />
}
