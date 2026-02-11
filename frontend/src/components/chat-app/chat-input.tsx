import { useRef, useState } from 'react'

function ChatInputForm({
  onSubmit,
  disabled,
}: {
  onSubmit: (message: string) => Promise<void>
  disabled?: boolean
}) {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const formRef = useRef<HTMLFormElement>(null)

  return (
    <form
      ref={formRef}
      action={async (formData: FormData) => {
        const message = (formData.get('message') as string)?.trim() ?? ''
        if (message && !disabled && !isSubmitting) {
          setIsSubmitting(true)
          try {
            await onSubmit(message)
            formRef.current?.reset()
          } finally {
            setIsSubmitting(false)
          }
        }
      }}
      className="flex gap-3 border-t border-gray-300 bg-gray-50 p-4 sm:p-4"
    >
      <textarea
        name="message"
        placeholder="Type a message..."
        rows={1}
        disabled={disabled || isSubmitting}
        className="min-h-11 max-h-32 flex-1 resize-none rounded-lg border border-gray-300 bg-white px-4 py-3 font-sans text-gray-900 placeholder:text-gray-400 focus:border-indigo-500 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed sm:min-h-11"
      />
      <button
        type="submit"
        disabled={disabled || isSubmitting}
        className="self-end rounded-lg border-0 bg-indigo-500 px-5 py-3 font-medium text-white hover:bg-indigo-600 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isSubmitting ? '…' : 'Send'}
      </button>
    </form>
  )
}

export function ChatInput({
  onSubmit,
  disabled,
}: {
  onSubmit: (message: string) => Promise<void>
  disabled?: boolean
}) {
  return <ChatInputForm onSubmit={onSubmit} disabled={disabled} />
}
