import { useRef, useState } from 'react'
import { FileUp, Loader2, UploadCloud } from 'lucide-react'

import { ACCEPTED_EXTENSIONS } from '../hooks/useDocumentUpload'

const PHASE_LABELS = {
  uploading: 'Uploading',
  processing: 'Processing',
}

/**
 * Drop target and file picker.
 *
 * The visible area is a label wrapping a real file input: pointer users can
 * drop or click anywhere on it, and keyboard users reach the input itself,
 * which the :focus-within styling makes visible on the whole zone.
 */
export default function UploadDropzone({ phase, progress, fileName, isBusy, onFile }) {
  const [isDragging, setIsDragging] = useState(false)
  const dragDepth = useRef(0)
  const inputRef = useRef(null)

  const handleDragEnter = (event) => {
    event.preventDefault()
    dragDepth.current += 1
    if (!isBusy) {
      setIsDragging(true)
    }
  }

  const handleDragLeave = (event) => {
    event.preventDefault()
    dragDepth.current = Math.max(0, dragDepth.current - 1)
    if (dragDepth.current === 0) {
      setIsDragging(false)
    }
  }

  const handleDrop = (event) => {
    event.preventDefault()
    dragDepth.current = 0
    setIsDragging(false)

    if (isBusy) {
      return
    }

    const [file] = event.dataTransfer.files
    if (file) {
      onFile(file)
    }
  }

  const handleChange = (event) => {
    const [file] = event.target.files
    if (file) {
      onFile(file)
    }
    // Allow the same file to be selected again after an error.
    event.target.value = ''
  }

  const percent = Math.round(progress * 100)

  return (
    <div className="dropzone-wrap">
      <label
        className={[
          'dropzone',
          isDragging ? 'dropzone--dragging' : '',
          isBusy ? 'dropzone--busy' : '',
        ]
          .filter(Boolean)
          .join(' ')}
        onDragEnter={handleDragEnter}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          ref={inputRef}
          className="visually-hidden"
          type="file"
          accept={ACCEPTED_EXTENSIONS.join(',')}
          onChange={handleChange}
          disabled={isBusy}
        />

        <span className="dropzone__icon" aria-hidden="true">
          {isBusy ? <Loader2 className="spin" size={20} /> : <UploadCloud size={20} />}
        </span>

        <span className="dropzone__copy">
          <span className="dropzone__title">
            {isBusy ? `${PHASE_LABELS[phase]} document` : 'Drop a document here'}
          </span>
          <span className="dropzone__text">
            {isBusy ? fileName : 'or select a file from your computer'}
          </span>
        </span>

        <span className="dropzone__formats">
          <FileUp size={11} aria-hidden="true" />
          PDF or TXT · up to 25 MB
        </span>

        {!isBusy ? <span className="dropzone__action">Choose file</span> : null}
      </label>

      {isBusy ? (
        <div className="upload-progress" aria-live="polite">
          <div className="upload-progress__head">
            <span>{phase === 'uploading' ? 'Transferring file' : 'Chunking and embedding'}</span>
            <span className="mono">{phase === 'uploading' ? `${percent}%` : 'In progress'}</span>
          </div>
          <div
            className={`progress${phase === 'processing' ? ' progress--indeterminate' : ''}`}
            role="progressbar"
            aria-label="Upload progress"
            aria-valuenow={phase === 'uploading' ? percent : undefined}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <span
              className="progress__bar"
              style={phase === 'uploading' ? { width: `${percent}%` } : undefined}
            />
          </div>
        </div>
      ) : null}
    </div>
  )
}
