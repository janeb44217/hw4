import { createContext, useContext, useState, type ReactNode } from 'react'
import type { PageResults } from './api'

// Holds the search results the chat agent pulled onto the page. The provider sits
// above the router, so results survive navigating to a product page and back.
// They're also kept in sessionStorage so a refresh doesn't lose them.

const STORAGE_KEY = 'cc_chat_results'

interface ChatResultsState {
  results: PageResults | null
  version: number // bumps on every new result set (used to replay the highlight animation)
  showResults: (results: PageResults) => void
  clearResults: () => void
}

const ChatResultsContext = createContext<ChatResultsState | null>(null)

function loadSaved(): PageResults | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as PageResults) : null
  } catch {
    return null
  }
}

export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<PageResults | null>(loadSaved)
  const [version, setVersion] = useState(0)

  function showResults(next: PageResults) {
    setResults(next)
    setVersion((v) => v + 1)
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  }

  function clearResults() {
    setResults(null)
    sessionStorage.removeItem(STORAGE_KEY)
  }

  return (
    <ChatResultsContext.Provider value={{ results, version, showResults, clearResults }}>
      {children}
    </ChatResultsContext.Provider>
  )
}

export function useChatResults(): ChatResultsState {
  const ctx = useContext(ChatResultsContext)
  if (!ctx) throw new Error('useChatResults must be used inside <ChatResultsProvider>')
  return ctx
}
