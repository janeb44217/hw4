import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  fetchChatHistory,
  fetchProduct,
  formatPrice,
  sendChatMessage,
  type ChatMessage,
  type PageResults,
} from '../api'
import { useAuth } from '../auth'
import { useChatResults } from '../chatResults'
import MiniBulldog from './MiniBulldog'

function greeting(firstName?: string): ChatMessage {
  return {
    role: 'assistant',
    content: `Hi${firstName ? ` ${firstName}` : ''}! I'm the Bulldog Assistant. Ask me about hoodies, sizes, stock, or gifts for your favorite Bulldog.`,
  }
}

// Context-aware starter questions (Problem 9). One tap sends the question.
function suggestionsFor(opts: { viewingName?: string; onProducts: boolean; loggedIn: boolean; hasHistory: boolean }) {
  if (opts.viewingName) {
    return ['Is this in stock in M?', 'What colors does this come in?', 'Show me something similar to this']
  }
  const base = opts.onProducts
    ? ['What hoodies do you have?', 'Gift ideas under $60', 'Anything for hockey fans?']
    : ['What hoodies do you have?', 'Gift for my mom under $60', 'What kinds of things do you sell?']
  if (opts.loggedIn && opts.hasHistory) return ['What did you recommend last time?', ...base.slice(0, 2)]
  return base
}

export default function ChatWidget() {
  const { user, loading } = useAuth()
  const [open, setOpen] = useState(false)
  // One gentle "Ask me!" nudge per visit, a few seconds after arriving.
  const [nudge, setNudge] = useState(false)
  useEffect(() => {
    if (sessionStorage.getItem('cc_nudged')) return
    const t = setTimeout(() => setNudge(true), 4000)
    return () => clearTimeout(t)
  }, [])
  function toggleChat() {
    setOpen((o) => !o)
    if (nudge) setNudge(false)
    sessionStorage.setItem('cc_nudged', '1')
  }
  const [messages, setMessages] = useState<ChatMessage[]>([greeting()])
  const [input, setInput] = useState('')
  const [thinking, setThinking] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)
  const { showResults } = useChatResults()
  const navigate = useNavigate()
  const location = useLocation()

  // Page context: which product page (if any) the shopper is looking at.
  const productId = location.pathname.match(/^\/products\/([^/]+)$/)?.[1] ?? null
  const [viewing, setViewing] = useState<{ id: string; name: string } | null>(null)
  useEffect(() => {
    if (!productId) return
    let cancelled = false
    fetchProduct(decodeURIComponent(productId))
      .then((p) => !cancelled && setViewing({ id: p.product_id, name: p.name }))
      .catch(() => !cancelled && setViewing(null))
    return () => {
      cancelled = true
    }
  }, [productId])
  const viewingNow = productId && viewing?.id === decodeURIComponent(productId) ? viewing : null

  // Put the agent's search matches on the Products page as product cards.
  function putOnPage(results: PageResults) {
    showResults(results)
    if (location.pathname !== '/products') navigate('/products')
  }

  // Reset the conversation when the shopper logs in or out; logged-in shoppers
  // get their saved history back from the server.
  useEffect(() => {
    if (loading) return
    let cancelled = false
    const start = greeting(user?.first_name)
    if (!user) {
      setMessages([start])
      return
    }
    fetchChatHistory().then((saved) => {
      if (!cancelled) setMessages([start, ...saved])
    })
    return () => {
      cancelled = true
    }
  }, [user, loading])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, thinking, open])

  async function send(e?: FormEvent, preset?: string) {
    e?.preventDefault()
    const text = (preset ?? input).trim()
    if (!text || thinking) return
    // The greeting is UI-only, so don't send it to the agent as history.
    const history = messages.slice(1)
    // Send the product from the URL immediately (the backend validates it); don't wait
    // for the name lookup that powers the "Viewing" chip.
    const pageProductId = productId ? decodeURIComponent(productId) : undefined
    setMessages((m) => [...m, { role: 'user', content: text, pageProductId }])
    setInput('')
    setThinking(true)
    try {
      const reply = await sendChatMessage(text, history, {
        path: location.pathname,
        product_id: pageProductId ?? null,
      })
      setMessages((m) => [...m, reply])
      if (reply.pageResults) putOnPage(reply.pageResults)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Something went wrong. Please try again.'
      setMessages((m) => [...m, { role: 'assistant', content: msg }])
    } finally {
      setThinking(false)
    }
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="chat-root">
      {open && (
        <div className="chat-panel" role="dialog" aria-label="Campus Customs chat">
          <div className="chat-header">
            <div className="chat-header-id">
              <span className="chat-header-avatar">
                <MiniBulldog size={42} />
                <span className="online-dot" aria-label="Online" />
              </span>
              <div>
                <p className="chat-title">Bulldog Assistant</p>
                <p className="chat-sub">
                  {user ? `Hi ${user.first_name}! Your chat is saved` : 'Online now · log in to save your chat'}
                </p>
              </div>
            </div>
            <button className="chat-close" aria-label="Close chat" onClick={() => setOpen(false)}>
              ×
            </button>
          </div>

          <div className="chat-messages">
            {messages.map((m, i) => (
              <div key={i} className={`chat-turn ${m.role}`}>
                <div className="chat-line">
                  {m.role === 'assistant' && <MiniBulldog size={28} />}
                  <div className={`chat-msg ${m.role}`}>{m.content.replace(/\*\*(.+?)\*\*/g, '$1')}</div>
                </div>
                {m.pageResults && (
                  <button className="chat-page-link" onClick={() => putOnPage(m.pageResults!)}>
                    🛍️ {m.pageResults.products.length} {m.pageResults.title.toLowerCase()} on the page · View
                  </button>
                )}
                {m.products && m.products.length > 0 && (
                  <div className="chat-cards">
                    {m.products.map((p) => (
                      <Link
                        to={`/products/${p.product_id}`}
                        className="chat-card"
                        key={p.product_id}
                      >
                        <img src={p.image_url} alt={p.name} loading="lazy" />
                        <div>
                          <p className="chat-card-name">{p.name}</p>
                          <p className="chat-card-price">
                            {formatPrice(p.price)}
                            {!p.in_stock && <span className="muted"> · Sold out</span>}
                          </p>
                        </div>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {thinking && (
              <div className="chat-line">
                <MiniBulldog size={28} />
                <div className="chat-msg assistant typing" aria-label="Assistant is fetching an answer">
                  <span>🐾</span>
                  <span>🐾</span>
                  <span>🐾</span>
                  <em>fetching…</em>
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>

          {!thinking && (
            <div className="chat-suggestions" aria-label="Suggested questions">
              {suggestionsFor({
                viewingName: viewingNow?.name,
                onProducts: location.pathname === '/products',
                loggedIn: !!user,
                hasHistory: messages.length > 1,
              }).map((q) => (
                <button key={q} className="suggestion" onClick={() => send(undefined, q)}>
                  {q}
                </button>
              ))}
            </div>
          )}
          {viewingNow && (
            <div className="chat-context" title="The assistant knows which item you're looking at">
              👀 Viewing: <strong>{viewingNow.name}</strong>
            </div>
          )}
          <form className="chat-input" onSubmit={send}>
            <textarea
              rows={1}
              maxLength={2000}
              placeholder={viewingNow ? 'Ask about this item…' : 'Ask about products…'}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
            />
            <button type="submit" className="btn btn-pink btn-sm" disabled={!input.trim() || thinking}>
              Send
            </button>
          </form>
        </div>
      )}

      {nudge && !open && (
        <button className="chat-nudge" onClick={toggleChat}>
          Need a size or a gift idea? <strong>Ask me!</strong>
        </button>
      )}
      <button
        className={open ? 'chat-fab open' : 'chat-fab'}
        aria-label={open ? 'Close chat' : 'Open chat with the Bulldog Assistant'}
        onClick={toggleChat}
      >
        {open ? <span className="chat-fab-x">×</span> : <MiniBulldog size={50} />}
      </button>
    </div>
  )
}
