import { Link } from 'react-router-dom'

const values = [
  {
    title: 'Rooted in New Haven',
    text: 'We are a local shop just steps from campus, run by people who love this city and this school.',
  },
  {
    title: 'Pride for every Bulldog',
    text: 'From first-years to fiftieth reunions, and from residential colleges to professional schools, we carry gear for every corner of the Yale community.',
  },
  {
    title: 'Quality you can feel',
    text: 'We pick fabrics and prints that hold up to cheering, washing, and years of wear.',
  },
]

export default function About() {
  return (
    <>
      <section className="section container">
        <div className="page-head">
          <p className="eyebrow">About Us</p>
          <h1>
            Made for the <span className="pink">Bulldog</span> in all of us
          </h1>
          <p className="lead">
            Campus Customs started with a simple idea: Yale pride deserves to be worn. We
            design and stock officially licensed apparel that helps students, alumni,
            families, and fans show up for Yale in style.
          </p>
        </div>

        <div className="reason-grid">
          {values.map((v) => (
            <div className="reason" key={v.title}>
              <h3 className="pink">{v.title}</h3>
              <p className="muted">{v.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="banner">
        <div className="container banner-inner">
          <h2>Come say hi</h2>
          <p>
            Visit us at <strong>57 Broadway, New Haven, CT 06511</strong>, or browse online
            and find the piece that shows off your Bulldog pride.
          </p>
          <Link to="/products" className="btn btn-pink">Browse Products</Link>
        </div>
      </section>
    </>
  )
}
