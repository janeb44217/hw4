import { useEffect, useState, type MouseEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchProduct, fetchSimilar, formatPrice, type ProductDetail as Product, type ProductSummary } from '../api'
import ProductCard from '../components/ProductCard'
import { useChatResults } from '../chatResults'

const LOW_STOCK = 5

export default function ProductDetail() {
  const { productId = '' } = useParams()
  const [product, setProduct] = useState<Product | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [size, setSize] = useState<string | null>(null)
  const { results } = useChatResults()
  const [similar, setSimilar] = useState<ProductSummary[]>([])

  useEffect(() => {
    setProduct(null)
    setError(null)
    setSize(null)
    setSimilar([])
    fetchProduct(productId)
      .then(setProduct)
      .catch(() => setError("We couldn't find that product."))
    fetchSimilar(productId)
      .then(setSimilar)
      .catch(() => setSimilar([]))
  }, [productId])

  function zoomTo(e: MouseEvent<HTMLDivElement>) {
    const r = e.currentTarget.getBoundingClientRect()
    e.currentTarget.style.setProperty('--zx', `${((e.clientX - r.left) / r.width) * 100}%`)
    e.currentTarget.style.setProperty('--zy', `${((e.clientY - r.top) / r.height) * 100}%`)
  }

  if (error) {
    return (
      <section className="section container page-head">
        <h1>{error}</h1>
        <Link to="/products" className="btn btn-pink">Back to Products</Link>
      </section>
    )
  }

  if (!product) {
    return (
      <section className="section container">
        <p className="muted">Loading…</p>
      </section>
    )
  }

  const totalStock = product.inventory.reduce((sum, s) => sum + s.quantity, 0)
  const selected = product.inventory.find((s) => s.size === size)

  return (
    <section className="section container">
      <Link to="/products" className="back-link">
        {results ? `← Back to ${results.title}` : '← All products'}
      </Link>

      <div className="detail">
        {/* Hover to inspect: the photo zooms toward the cursor, like holding the shirt up close. */}
        <div className="detail-img" onMouseMove={zoomTo}>
          <img src={product.image_url} alt={product.name} />
          <span className="zoom-hint" aria-hidden="true">🔍 Hover to zoom</span>
        </div>

        <div className="detail-info">
          <p className="eyebrow">{product.garment_type}</p>
          <h1>{product.name}</h1>
          <p className="detail-price">{formatPrice(product.price)}</p>
          <p className="detail-desc">{product.description}</p>

          <div className="detail-block">
            <h3>Colors</h3>
            <div className="chip-row">
              {product.colors.map((c) => (
                <span className="chip" key={c}>{c}</span>
              ))}
            </div>
          </div>

          <div className="detail-block">
            <h3>Sizes &amp; stock</h3>
            <div className="size-grid">
              {product.inventory.map((s) => (
                <button
                  key={s.size}
                  className={[
                    'size-btn',
                    s.quantity === 0 ? 'out' : '',
                    s.size === size ? 'active' : '',
                  ].join(' ')}
                  disabled={s.quantity === 0}
                  onClick={() => setSize(s.size)}
                >
                  <span className="size-label">{s.size}</span>
                  <span className="size-qty">
                    {s.quantity === 0 ? 'Sold out' : `${s.quantity} left`}
                  </span>
                </button>
              ))}
            </div>
            <p className="muted small">
              {totalStock === 0
                ? 'This item is currently sold out in every size.'
                : selected
                  ? selected.quantity <= LOW_STOCK
                    ? `Only ${selected.quantity} left in ${selected.size}. Grab it soon!`
                    : `${selected.size} is in stock.`
                  : `${totalStock} in stock across all sizes. Pick a size to check availability.`}
            </p>
          </div>

          <div className="detail-block">
            <h3>Tags</h3>
            <p className="muted small">{product.search_tags.join(' · ')}</p>
          </div>
        </div>
      </div>

      {similar.length > 0 && (
        <div className="similar">
          <h2>
            You might also <span className="pink">like</span>
          </h2>
          <p className="muted small">Similar styles that are in stock now</p>
          <div className="product-grid">
            {similar.map((p, i) => (
              <ProductCard product={p} index={i} key={p.product_id} />
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
