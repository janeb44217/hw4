// Client for the Campus Customs FastAPI backend (backend/main.py).
// In dev, Vite proxies /api and /images to http://127.0.0.1:8000.

export interface ProductSummary {
  product_id: string
  name: string
  garment_type: string
  category: string
  price: number
  short_description: string
  colors: string[]
  image_url: string
  in_stock: boolean
  sizes_in_stock: string[]
}

export interface StockLevel {
  size: string
  quantity: number
}

export interface ProductDetail {
  product_id: string
  name: string
  garment_type: string
  description: string
  price: number
  colors: string[]
  search_tags: string[]
  image_url: string
  inventory: StockLevel[]
}

export interface ProductCard {
  product_id: string
  name: string
  price: number
  image_url: string
  in_stock: boolean
}

// Search matches the agent sends for the page (see POST /api/chat contract).
export interface PageResults {
  title: string
  products: ProductSummary[]
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  products?: ProductCard[]
  pageResults?: PageResults
  pageProductId?: string // product page the shopper was on when they sent it
}

// Where the shopper is when they send a message, so "do you have this in pink?" works.
export interface PageContext {
  path: string
  product_id: string | null
}

interface ChatResponse {
  reply: string
  products: ProductCard[]
  page_results: PageResults | null
}

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Request failed (${res.status})`)
  return res.json() as Promise<T>
}

export function fetchProducts(): Promise<ProductSummary[]> {
  return getJson('/api/products')
}

export function fetchProduct(productId: string): Promise<ProductDetail> {
  return getJson(`/api/products/${encodeURIComponent(productId)}`)
}

// In-stock alternatives (same engine as the agent's find_similar_products tool).
export function fetchSimilar(productId: string): Promise<ProductSummary[]> {
  return getJson(`/api/products/${encodeURIComponent(productId)}/similar`)
}

export function formatPrice(price: number): string {
  return `$${price.toFixed(2)}`
}

// Sends one chat turn to the PydanticAI agent behind POST /api/chat.
// `history` is the conversation so far (used for guests; logged-in users'
// history comes from the database on the server).
export async function sendChatMessage(
  message: string,
  history: ChatMessage[],
  page: PageContext,
): Promise<ChatMessage> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      page,
      // Only used for guests; logged-in history is loaded from the database.
      history: history.slice(-20).map((m) => ({
        role: m.role,
        content: m.content,
        products: m.products ?? [],
        page_product_id: m.pageProductId ?? null,
      })),
    }),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail ?? 'The shopping assistant is unavailable right now.')
  const { reply, products, page_results } = data as ChatResponse
  return { role: 'assistant', content: reply, products, pageResults: page_results ?? undefined }
}

interface SavedChatMessage {
  role: 'user' | 'assistant'
  content: string
  products: ProductCard[]
  page_product_id: string | null
  created_at: string
}

// The logged-in shopper's saved conversation (empty for guests).
export async function fetchChatHistory(): Promise<ChatMessage[]> {
  const res = await fetch('/api/chat/history', { credentials: 'same-origin' })
  if (!res.ok) return []
  const saved = (await res.json()) as SavedChatMessage[]
  return saved.map((m) => ({
    role: m.role,
    content: m.content,
    products: m.products,
    pageProductId: m.page_product_id ?? undefined,
  }))
}

// ---------- Auth ----------
// The session lives in an HttpOnly cookie set by the backend, so the browser
// sends it automatically and JavaScript never sees the token.

export interface User {
  id: number
  first_name: string
  last_name: string
  email: string
  created_at: string
}

export interface RegisterInput {
  first_name: string
  last_name: string
  email: string
  password: string
}

async function postJson<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail ?? `Request failed (${res.status})`)
  return data as T
}

export async function fetchCurrentUser(): Promise<User | null> {
  const res = await fetch('/api/auth/me', { credentials: 'same-origin' })
  return res.ok ? res.json() : null
}

export function loginRequest(email: string, password: string): Promise<User> {
  return postJson('/api/auth/login', { email, password })
}

export function registerRequest(input: RegisterInput): Promise<User> {
  return postJson('/api/auth/register', input)
}

export function logoutRequest(): Promise<{ ok: boolean }> {
  return postJson('/api/auth/logout')
}
