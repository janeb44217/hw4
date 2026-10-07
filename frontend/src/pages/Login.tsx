import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

export default function Login() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from ?? '/'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (user) return <Navigate to={from} replace />

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(email, password)
      navigate(from, { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
      setPassword('')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="section container auth-wrap">
      <form className="auth-card" onSubmit={handleSubmit} noValidate>
        <h1>
          Welcome back, <span className="pink">Bulldog</span>
        </h1>
        <p className="muted">Log in to chat with our shopping assistant and track your favorites.</p>

        <label>
          Email
          <input
            type="email"
            name="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            name="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>

        {error && <p className="form-error" role="alert">{error}</p>}

        <button
          type="submit"
          className="btn btn-pink btn-block"
          disabled={submitting || !email || !password}
        >
          {submitting ? 'Logging in…' : 'Log In'}
        </button>

        <p className="muted small">
          New here? <Link to="/create-account" className="pink">Create an account</Link>
        </p>
      </form>
    </section>
  )
}
