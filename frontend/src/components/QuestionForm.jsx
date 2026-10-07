import { useRef } from 'react'
import { ArrowRight, Loader2 } from 'lucide-react'

const EXAMPLE_QUESTIONS = [
  'What is a text embedding and why is it useful?',
  'How does cosine distance measure similarity?',
  'What is the HNSW vector index for?',
  'How does the document ingestion pipeline work?',
]

const SOURCE_COUNTS = [3, 5, 8, 12]

export default function QuestionForm({
  question,
  onQuestionChange,
  topK,
  onTopKChange,
  isLoading,
  onSubmit,
}) {
  const inputRef = useRef(null)
  const canSubmit = question.trim().length > 0 && !isLoading

  const handleSubmit = (event) => {
    event.preventDefault()
    if (canSubmit) {
      onSubmit()
    }
  }

  // Keep the Enter key free for line breaks; send on the usual shortcut.
  const handleKeyDown = (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter' && canSubmit) {
      event.preventDefault()
      onSubmit()
    }
  }

  return (
    <form className="ask-form" onSubmit={handleSubmit}>
      <div className="field">
        <label className="field__label" htmlFor="question">
          Your question
        </label>
        <textarea
          ref={inputRef}
          id="question"
          className="field__input"
          rows={3}
          placeholder="Ask anything about the documents in your collection…"
          value={question}
          onChange={(event) => onQuestionChange(event.target.value)}
          onKeyDown={handleKeyDown}
          spellCheck="true"
        />

        <div className="field__footer">
          <div className="field__controls">
            <label className="select" htmlFor="top-k">
              <span className="select__label">Sources</span>
              <select
                id="top-k"
                className="select__input"
                value={topK}
                onChange={(event) => onTopKChange(Number(event.target.value))}
              >
                {SOURCE_COUNTS.map((count) => (
                  <option key={count} value={count}>
                    {count}
                  </option>
                ))}
              </select>
            </label>
            <p className="field__shortcut" aria-hidden="true">
              <kbd className="kbd">⌘</kbd>
              <kbd className="kbd">↵</kbd>
              to ask
            </p>
          </div>

          <button type="submit" className="button button--primary" disabled={!canSubmit}>
            {isLoading ? (
              <>
                <Loader2 className="spin" size={15} aria-hidden="true" />
                Searching
              </>
            ) : (
              <>
                Ask
                <ArrowRight size={15} aria-hidden="true" />
              </>
            )}
          </button>
        </div>
      </div>

      <div className="examples">
        <p className="examples__label" id="examples-label">
          Start with
        </p>
        <ul className="examples__list" aria-labelledby="examples-label">
          {EXAMPLE_QUESTIONS.map((example) => (
            <li key={example}>
              <button
                type="button"
                className="chip"
                onClick={() => {
                  onQuestionChange(example)
                  inputRef.current?.focus()
                }}
                disabled={isLoading}
              >
                {example}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </form>
  )
}
