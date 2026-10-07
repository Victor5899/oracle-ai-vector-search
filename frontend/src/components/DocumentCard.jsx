import { CheckCircle2, FileText, History } from 'lucide-react'

const STATUS_PRESENTATION = {
  processed: { label: 'Processed', icon: CheckCircle2, tone: 'success' },
  already_processed: { label: 'Already indexed', icon: History, tone: 'neutral' },
}

const FALLBACK = { label: 'Stored', icon: CheckCircle2, tone: 'neutral' }

/** Result of one ingested document: name, counts and processing status. */
export default function DocumentCard({ document }) {
  const presentation = STATUS_PRESENTATION[document.status] ?? FALLBACK
  const StatusIcon = presentation.icon

  return (
    <article className="doc-card">
      <header className="doc-card__head">
        <FileText className="doc-card__file-icon" size={15} aria-hidden="true" />
        <h3 className="doc-card__name" title={document.fileName}>
          {document.fileName}
        </h3>
        <span className={`tag tag--${presentation.tone}`}>
          <StatusIcon size={11} aria-hidden="true" />
          {presentation.label}
        </span>
      </header>

      <dl className="doc-card__metrics">
        <div className="metric">
          <dt className="metric__label">Chunks</dt>
          <dd className="metric__value mono">{document.chunks}</dd>
        </div>
        <div className="metric">
          <dt className="metric__label">Embeddings</dt>
          <dd className="metric__value mono">{document.embeddings}</dd>
        </div>
        <div className="metric">
          <dt className="metric__label">Document</dt>
          <dd className="metric__value mono">{document.documentId}</dd>
        </div>
      </dl>
    </article>
  )
}
