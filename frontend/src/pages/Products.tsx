import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchProducts, type ProductSummary } from '../api'
import { useChatResults } from '../chatResults'
import ProductCard from '../components/ProductCard'

// Categories come from the backend (ProductSummary.category), which groups the
// catalogue's 22 inconsistent garment_type values.
const CATEGORIES = ['All', 'Hoodies', 'Crewnecks', 'Quarter-Zips', 'T-Shirts', 'Jackets & Fleece', 'Long Sleeves']

const SORTS = {
  featured: { label: 'Name (A–Z)', fn: (a: ProductSummary, b: ProductSummary) => a.name.localeCompare(b.name) },
  'price-asc': { label: 'Price: low to high', fn: (a: ProductSummary, b: ProductSummary) => a.price - b.price || a.name.localeCompare(b.name) },
  'price-desc': { label: 'Price: high to low', fn: (a: ProductSummary, b: ProductSummary) => b.price - a.price || a.name.localeCompare(b.name) },
} as const
type SortKey = keyof typeof SORTS

const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']

const PRICE_CAPS = [
  { value: '', label: 'Any price' },
  { value: '40', label: 'Under $40' },
  { value: '60', label: 'Under $60' },
  { value: '75', label: 'Under $75' },
]

export default function Products() {
  const [products, setProducts] = useState<ProductSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { results, version, clearResults } = useChatResults()

  // Filters live in the URL (?cat=Hoodies&sort=price-asc&size=XL&max=60), so the back
  // button, refresh, and shared links all keep them.
  const [params, setParams] = useSearchParams()
  const type = params.get('cat') ?? 'All'
  const query = params.get('q') ?? ''
  const sort = (params.get('sort') as SortKey) in SORTS ? (params.get('sort') as SortKey) : 'featured'
  const size = SIZES.includes(params.get('size') ?? '') ? (params.get('size') as string) : ''
  const maxPrice = params.get('max') ?? ''

  function setParam(key: string, value: string | null) {
    const next = new URLSearchParams(params)
    if (value === null || value === '' || (key === 'cat' && value === 'All') || (key === 'sort' && value === 'featured')) {
      next.delete(key)
    } else {
      next.set(key, value)
    }
    setParams(next, { replace: key === 'q' })
  }

  const activeFilters = [size !== '', maxPrice !== '', sort !== 'featured', type !== 'All', query !== ''].filter(Boolean).length

  useEffect(() => {
    fetchProducts()
      .then(setProducts)
      .catch(() => setError("We couldn't load the catalog. Is the backend running?"))
      .finally(() => setLoading(false))
  }, [])

  // New results from the chat: bring them into view.
  useEffect(() => {
    if (version > 0) window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [version])

  // Sort / size / price apply to both the catalogue and chat results.
  function refine(list: ProductSummary[]) {
    return list
      .filter((p) => !size || (p.sizes_in_stock ?? []).includes(size))
      .filter((p) => !maxPrice || p.price < Number(maxPrice))
      .sort(SORTS[sort].fn)
  }

  const visible = refine(
    products.filter((p) => {
      const matchesType = type === 'All' || p.category === type
      const q = query.trim().toLowerCase()
      const matchesQuery =
        !q || p.name.toLowerCase().includes(q) || p.short_description.toLowerCase().includes(q)
      return matchesType && matchesQuery
    }),
  )
  const chatVisible = results ? refine([...results.products]) : []

  const refineBar = (
    <div className="refine-bar">
      <label className="refine-field">
        <span>Sort</span>
        <select value={sort} onChange={(e) => setParam('sort', e.target.value)}>
          {Object.entries(SORTS).map(([k, v]) => (
            <option key={k} value={k}>{v.label}</option>
          ))}
        </select>
      </label>
      <label className="refine-field">
        <span>Price</span>
        <select value={maxPrice} onChange={(e) => setParam('max', e.target.value)}>
          {PRICE_CAPS.map((c) => (
            <option key={c.value} value={c.value}>{c.label}</option>
          ))}
        </select>
      </label>
      <label className="refine-field">
        <span>Available in</span>
        <select value={size} onChange={(e) => setParam('size', e.target.value)}>
          <option value="">Any size</option>
          {SIZES.map((sz) => (
            <option key={sz} value={sz}>Size {sz}</option>
          ))}
        </select>
      </label>
      {activeFilters > 0 && (
        <button className="link-btn" onClick={() => setParams(new URLSearchParams())}>
          Clear filters ({activeFilters})
        </button>
      )}
    </div>
  )

  const empty = (
    <div className="placeholder-panel">
      <p className="pink">No matches</p>
      <p className="muted">Try a different search, category, or price.</p>
    </div>
  )

  return (
    <section className="section container">
      <div className="page-head">
        <p className="eyebrow">Products</p>
        <h1>
          Gear up, <span className="pink">Bulldogs</span>
        </h1>
        <p className="lead">
          Every piece in our collection is a great way to show Bulldog pride, from classic
          crewnecks to sport-specific hoodies.
        </p>
      </div>

      {results ? (
        <div className="chat-results" key={version}>
          <div className="chat-results-head">
            <div>
              <p className="eyebrow">💬 From the Bulldog Assistant</p>
              <h2>{results.title}</h2>
              <p className="muted small">
                {chatVisible.length} of {results.products.length}{' '}
                {results.products.length === 1 ? 'match' : 'matches'} · click any item for full details
              </p>
            </div>
            <button className="btn btn-outline btn-sm" onClick={clearResults}>
              Show all products
            </button>
          </div>
          {refineBar}
          <div className="product-grid">
            {chatVisible.map((p, i) => (
              <ProductCard product={p} index={i} key={p.product_id} />
            ))}
          </div>
          {chatVisible.length === 0 && empty}
        </div>
      ) : (
        <>
          <div className="product-toolbar">
            <input
              className="search-input"
              type="search"
              placeholder="Search hoodies, colleges, sports…"
              value={query}
              onChange={(e) => setParam('q', e.target.value)}
            />
            <div className="chip-row">
              {CATEGORIES.map((t) => (
                <button
                  key={t}
                  className={t === type ? 'chip active' : 'chip'}
                  onClick={() => setParam('cat', t)}
                >
                  {t}
                </button>
              ))}
            </div>
            {refineBar}
          </div>

          {loading && <p className="muted">Fetching the latest gear…</p>}
          {error && <div className="placeholder-panel"><p className="pink">{error}</p></div>}

          {!loading && !error && (
            <>
              <p className="muted small">
                {visible.length} {visible.length === 1 ? 'product' : 'products'}
              </p>
              <div className="product-grid">
                {visible.map((p, i) => (
                  <ProductCard product={p} index={i} key={p.product_id} />
                ))}
              </div>
              {visible.length === 0 && empty}
            </>
          )}
        </>
      )}
    </section>
  )
}
