/** Placeholder shown while retrieval and generation are running. */
export default function AnswerSkeleton() {
  return (
    <div className="answer" aria-hidden="true">
      <div className="answer__head">
        <p className="eyebrow">Answer</p>
        <span className="answer__working">
          <span className="answer__working-dot" />
          Retrieving passages
        </span>
      </div>

      <div className="skeleton">
        <span className="skeleton__line" />
        <span className="skeleton__line" />
        <span className="skeleton__line skeleton__line--short" />
        <span className="skeleton__line" />
        <span className="skeleton__line skeleton__line--medium" />
      </div>
    </div>
  )
}
