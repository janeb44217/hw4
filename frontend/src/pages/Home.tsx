import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchProducts, type ProductSummary } from '../api'
import Bulldog from '../components/Bulldog'
import Pennant from '../components/Pennant'
import Reveal from '../components/Reveal'

// Real catalogue items pinned around the mascot like Polaroids on a dorm wall.
const POLAROIDS = [
  { id: 'champion-reverse-weave-hoodie-1', caption: 'the classic', tilt: -8 },
  { id: 'yale-sports-hoodie-hockey', caption: 'game day', tilt: 6 },
  { id: 'davenport-college-crewneck', caption: 'rep your college', tilt: -4 },
]

// Category pennants link straight into the filtered Products page (Problem 9 URL filters).
const CATEGORY_PENNANTS = [
  { cat: 'Hoodies', note: 'warmest seats in the house' },
  { cat: 'Crewnecks', note: 'colleges, sports & family' },
  { cat: 'Quarter-Zips', note: 'office-hours ready' },
  { cat: 'T-Shirts', note: 'move-in day staples' },
  { cat: 'Jackets & Fleece', note: 'for real New Haven winters' },
]

const PATCHES = [
  { icon: '★', title: 'Officially licensed', text: 'Every design is approved Yale merchandise, so the pride is authentic.' },
  { icon: '✂', title: 'Made to be worn', text: 'Soft fleece, sturdy stitching, and fits that last many seasons.' },
  { icon: '♥', title: 'For every Bulldog', text: 'Students, alumni, grad schools, sports fans, and proud relatives.' },
]

export default function Home() {
  const [products, setProducts] = useState<ProductSummary[]>([])

  useEffect(() => {
    fetchProducts().then(setProducts).catch(() => setProducts([]))
  }, [])

  const count = (cat: string) => products.filter((p) => p.category === cat).length
  const sizesInStock = products.reduce((n, p) => n + p.sizes_in_stock.length, 0)

  return (
    <>
      <section className="hero">
        <div className="container hero-inner">
          <div className="hero-copy">
            <p className="eyebrow">New Haven, CT · 57 Broadway</p>
            <h1 className="hero-title">
              Wear your <span className="pink">Bulldog</span> pride
            </h1>
            <p className="hero-script">everywhere you go.</p>
            <p className="lead">
              Campus Customs makes Yale apparel for game days, study nights, reunions, and every
              lazy Sunday in between. Grab a hoodie, cheer louder, and let everyone know where your
              heart lives.
            </p>
            <div className="hero-actions">
              <Link to="/products" className="btn btn-pink btn-lg">Shop the collection →</Link>
              <Link to="/about" className="btn btn-outline btn-lg">Our story</Link>
            </div>
            {products.length > 0 && (
              <dl className="hero-stats">
                <div>
                  <dt>{products.length}</dt>
                  <dd>styles</dd>
                </div>
                <div>
                  <dt>{sizesInStock}</dt>
                  <dd>sizes on the shelf</dd>
                </div>
                <div>
                  <dt>XS–XXL</dt>
                  <dd>fits for everyone</dd>
                </div>
              </dl>
            )}
          </div>

          <div className="hero-stage">
            <Pennant text="BOOLA BOOLA" className="hero-pennant" />
            <div className="hero-spotlight" aria-hidden="true" />
            <Bulldog />
            {POLAROIDS.map((p, i) => (
              <Link
                to={`/products/${p.id}`}
                key={p.id}
                className={`polaroid polaroid-${i}`}
                style={{ ['--tilt' as string]: `${p.tilt}deg` }}
              >
                <img src={`/images/${p.id}.jpg`} alt="" loading="eager" />
                <span>{p.caption}</span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="section container">
        <Reveal>
          <div className="section-head">
            <p className="eyebrow">Shop by spirit</p>
            <h2>Pick your pennant</h2>
          </div>
        </Reveal>
        <div className="pennant-grid">
          {CATEGORY_PENNANTS.map((c, i) => (
            <Reveal key={c.cat} delay={i * 70}>
              <Link to={`/products?cat=${encodeURIComponent(c.cat)}`} className="cat-pennant">
                <span className="cat-pennant-name">{c.cat}</span>
                <span className="cat-pennant-note">{c.note}</span>
                {products.length > 0 && <span className="cat-pennant-count">{count(c.cat)} styles</span>}
              </Link>
            </Reveal>
          ))}
        </div>
      </section>

      <section className="banner">
        <div className="container banner-inner">
          <Reveal>
            <p className="banner-script">big pride.</p>
            <h2>
              Bigger <span className="pink">Yale.</span>
            </h2>
            <p>
              Our gear is a great way to show Bulldog pride, whether you are cheering at The Game,
              walking across Old Campus, or sending love from across the country.
            </p>
            <Link to="/products" className="btn btn-pink btn-lg">Find your fit</Link>
          </Reveal>
        </div>
      </section>

      <section className="section container">
        <div className="patch-grid">
          {PATCHES.map((r, i) => (
            <Reveal key={r.title} delay={i * 90}>
              <div className="patch">
                <span className="patch-icon" aria-hidden="true">{r.icon}</span>
                <h3>{r.title}</h3>
                <p className="muted">{r.text}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>
    </>
  )
}
