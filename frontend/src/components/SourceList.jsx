import { Layers } from 'lucide-react'

/** Cosine distance grows as meaning diverges, so closeness is its inverse. */
function closeness(distance) {
  return Math.min(100, Math.max(0, (1 - distance) * 100))
}

/**
 * Passages the answer was built from. Deliberately quieter than the answer
 * itself: small type, hairline separators, no card chrome.
 */
export default function SourceList({ sources }) {
  if (sources.length === 0) {
    return null
  }

  return (
    <section className="sources" aria-labelledby="sources-title">
      <p className="eyebrow sources__title" id="sources-title">
        <Layers size={13} aria-hidden="true" />
        Retrieved sources · {sources.length}
      </p>

      <ol className="sources__list">
        {sources.map((source, index) => (
          <li
            key={source.chunk_id}
            className="source"
            style={{ '--source-delay': `${index * 55}ms` }}
          >
            <div className="source__identity">
              <p className="source__index">Source {String(index + 1).padStart(2, '0')}</p>
              <p className="source__meta">
                Document {source.document_id} · Chunk {source.chunk_index}
              </p>
            </div>

            <div className="source__measure">
              <p className="source__distance mono">
                Distance {Number.isFinite(Number(source.distance)) ? Number(source.distance).toFixed(4) : '—'}
              </p>
              <div className="source__scale" aria-hidden="true">
                <span style={{ width: `${closeness(Number(source.distance))}%` }} />
              </div>
              <p className="source__id mono">Chunk ID {source.chunk_id}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}
