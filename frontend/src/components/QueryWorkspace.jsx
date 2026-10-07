import { MessagesSquare } from 'lucide-react'

import Alert from './Alert'
import AnswerCard from './AnswerCard'
import AnswerSkeleton from './AnswerSkeleton'
import EmptyState from './EmptyState'
import QuestionForm from './QuestionForm'
import SourceList from './SourceList'

/** Right column and primary interaction: ask, then read the grounded answer. */
export default function QueryWorkspace({
  question,
  onQuestionChange,
  topK,
  onTopKChange,
  onSubmit,
  answer,
}) {
  const { status, result, error, reset } = answer

  return (
    <section className="panel panel--primary" id="ask" aria-labelledby="ask-title">
      <div className="panel__head">
        <p className="eyebrow">
          <MessagesSquare size={13} aria-hidden="true" />
          Ask
        </p>
        <h2 className="panel__title panel__title--lead" id="ask-title">
          Question your document collection
        </h2>
      </div>

      <QuestionForm
        question={question}
        onQuestionChange={onQuestionChange}
        topK={topK}
        onTopKChange={onTopKChange}
        isLoading={status === 'loading'}
        onSubmit={onSubmit}
      />

      <div className="results" aria-live="polite" aria-busy={status === 'loading'}>
        {status === 'idle' ? <EmptyState /> : null}
        {status === 'loading' ? <AnswerSkeleton /> : null}
        {status === 'error' && error ? (
          <Alert title="No answer returned" message={error} onDismiss={reset} />
        ) : null}
        {status === 'ready' && result ? (
          <>
            <AnswerCard question={result.question} answer={result.answer} />
            <SourceList sources={result.sources} />
          </>
        ) : null}
      </div>
    </section>
  )
}
