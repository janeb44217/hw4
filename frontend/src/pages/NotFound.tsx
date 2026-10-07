import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <section className="section container page-head">
      <h1>
        This page ran off <span className="pink">chasing a ball</span>
      </h1>
      <p className="lead">We couldn't find what you were looking for.</p>
      <Link to="/" className="btn btn-pink">Back to Home</Link>
    </section>
  )
}
