import { Library } from 'lucide-react'

import Alert from './Alert'
import DocumentCard from './DocumentCard'
import UploadDropzone from './UploadDropzone'

/** Left column: bring documents into the collection and review the result. */
export default function DocumentWorkspace({ upload }) {
  const { documents, phase, progress, fileName, error, isBusy, upload: send, reset } = upload

  return (
    <section className="panel" id="documents" aria-labelledby="documents-title">
      <div className="panel__head">
        <p className="eyebrow">
          <Library size={13} aria-hidden="true" />
          Document workspace
        </p>
        <h2 className="panel__title" id="documents-title">
          Add a source document
        </h2>
        <p className="panel__hint">
          Files are split into overlapping passages, embedded as vectors and stored in Oracle so
          they can be searched by meaning.
        </p>
      </div>

      <UploadDropzone
        phase={phase}
        progress={progress}
        fileName={fileName}
        isBusy={isBusy}
        onFile={send}
      />

      {phase === 'error' && error ? (
        <Alert title="Upload failed" message={error} onDismiss={reset} />
      ) : null}

      {documents.length > 0 ? (
        <div className="doc-list">
          <p className="eyebrow doc-list__label">
            In this session · {documents.length}
          </p>
          {documents.map((document) => (
            <DocumentCard key={document.key} document={document} />
          ))}
        </div>
      ) : null}
    </section>
  )
}
