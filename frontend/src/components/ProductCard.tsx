import { Link } from 'react-router-dom'
import { type ProductSummary } from '../api'

const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']

// One product tile, styled like a garment on the rack with a paper hang tag.
// Used by the full catalogue grid and by the results the chat agent pulls onto
// the page, so both open the same /products/:id detail view.
export default function ProductCard({ product, index = 0 }: { product: ProductSummary; index?: number }) {
  const sizes = product.sizes_in_stock ?? []
  const fewLeft = sizes.length > 0 && sizes.length <= 3
  const dollars = Number.isInteger(product.price) ? `$${product.price}` : `$${product.price.toFixed(2)}`

  return (
    <Link
      to={`/products/${product.product_id}`}
      className="product-card"
      style={{ ['--i' as string]: Math.min(index, 12) }}
    >
      <div className="product-img">
        <img src={product.image_url} alt={product.name} loading="lazy" />
        <span className="hang-tag" aria-label={`Price ${dollars}`}>
          <span className="hang-tag-hole" aria-hidden="true" />
          {dollars}
        </span>
        {!product.in_stock && <span className="ribbon ribbon-out">Sold out</span>}
        {fewLeft && <span className="ribbon">Only {sizes.length} sizes left</span>}
        <span className="quick-look" aria-hidden="true">View details →</span>
      </div>
      <div className="product-body">
        <p className="product-cat">{product.category}</p>
        <h3>{product.name}</h3>
        <p className="muted small">{product.short_description}</p>
        <p className="card-sizes" aria-label="Sizes in stock">
          {SIZES.map((sz) => (
            <span key={sz} className={sizes.includes(sz) ? 'sz' : 'sz out'}>
              {sz}
            </span>
          ))}
        </p>
      </div>
    </Link>
  )
}
