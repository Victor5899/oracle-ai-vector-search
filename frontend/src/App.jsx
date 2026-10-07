import { useState } from 'react'

import AppHeader from './components/AppHeader'
import DocumentWorkspace from './components/DocumentWorkspace'
import QueryWorkspace from './components/QueryWorkspace'
import { useAnswer } from './hooks/useAnswer'
import { useDocumentUpload } from './hooks/useDocumentUpload'
import { useHealth } from './hooks/useHealth'

const DEFAULT_TOP_K = 5

export default function App() {
  const [question, setQuestion] = useState('')
  const [topK, setTopK] = useState(DEFAULT_TOP_K)

  const health = useHealth()
  const upload = useDocumentUpload()
  const answer = useAnswer()

  return (
    <div className="shell">
      <a className="skip-link" href="#ask">
        Skip to question
      </a>

      <AppHeader health={health} />

      <main className="workspace">
        <div className="workspace__column workspace__column--documents">
          <DocumentWorkspace upload={upload} />
        </div>
        <div className="workspace__column workspace__column--ask">
          <QueryWorkspace
            question={question}
            onQuestionChange={setQuestion}
            topK={topK}
            onTopKChange={setTopK}
            onSubmit={() => answer.ask(question, topK)}
            answer={answer}
          />
        </div>
      </main>

      <footer className="footer">
        <p>Answers are generated from retrieved passages and cite the sources they came from.</p>
      </footer>
    </div>
  )
}
