import { useEffect, useState } from 'react'
import { Check, Copy, Info } from 'lucide-react'

const NOT_FOUND_ANSWER = 'The information was not found in the provided documents.'

/** The generated answer, kept typographically plain and unadorned. */
export default function AnswerCard({ question, answer }) {
  const [copied, setCopied] = useState(false)
  const unanswered = answer.trim() === NOT_FOUND_ANSWER

  useEffect(() => {
    if (!copied) {
      return undefined
    }

    const timer = window.setTimeout(() => setCopied(false), 2000)
    return () => window.clearTimeout(timer)
  }, [copied])

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(answer)
      setCopied(true)
    } catch {
      // Clipboard access can be denied; the answer stays selectable.
    }
  }

  return (
    <div className="answer">
      <div className="answer__head">
        <p className="eyebrow">Answer</p>
        <button type="button" className="button button--quiet" onClick={handleCopy}>
          {copied ? (
            <>
              <Check size={13} aria-hidden="true" />
              Copied
            </>
          ) : (
            <>
              <Copy size={13} aria-hidden="true" />
              Copy
            </>
          )}
        </button>
      </div>

      <p className="answer__question">{question}</p>

      {unanswered ? (
        <p className="answer__notice">
          <Info size={15} aria-hidden="true" />
          {answer}
        </p>
      ) : (
        <p className="answer__body">{answer}</p>
      )}
    </div>
  )
}
