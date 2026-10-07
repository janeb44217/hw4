import { useState, type ChangeEvent, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

const MIN_PASSWORD_LENGTH = 8

export default function CreateAccount() {
  const { user, register } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    confirm: '',
  })
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (user) return <Navigate to="/" replace />

  const update = (field: keyof typeof form) => (e: ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [field]: e.target.value })

  const tooShort = form.password.length > 0 && form.password.length < MIN_PASSWORD_LENGTH
  const mismatch = form.confirm.length > 0 && form.password !== form.confirm

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (form.password.length < MIN_PASSWORD_LENGTH) {
      setError(`Password must be at least ${MIN_PASSWORD_LENGTH} characters.`)
      return
    }
    if (form.password !== form.confirm) {
      setError('Passwords do not match.')
      return
    }
    setSubmitting(true)
    try {
      await register({
        first_name: form.first_name,
        last_name: form.last_name,
        email: form.email,
        password: form.password,
      })
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="section container auth-wrap">
      <form className="auth-card" onSubmit={handleSubmit} noValidate>
        <h1>
          Join the <span className="pink">pack</span>
        </h1>
        <p className="muted">Create an account to save favorites and get personalized picks.</p>

        <div className="field-row">
          <label>
            First name
            <input
              type="text"
              name="first_name"
              autoComplete="given-name"
              value={form.first_name}
              onChange={update('first_name')}
              required
            />
          </label>
          <label>
            Last name
            <input
              type="text"
              name="last_name"
              autoComplete="family-name"
              value={form.last_name}
              onChange={update('last_name')}
              required
            />
          </label>
        </div>
        <label>
          Email
          <input
            type="email"
            name="email"
            autoComplete="email"
            value={form.email}
            onChange={update('email')}
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            name="password"
            autoComplete="new-password"
            value={form.password}
            onChange={update('password')}
            aria-invalid={tooShort}
            required
          />
          <span className={tooShort ? 'field-hint bad' : 'field-hint'}>
            At least {MIN_PASSWORD_LENGTH} characters
          </span>
        </label>
        <label>
          Confirm password
          <input
            type="password"
            name="confirm"
            autoComplete="new-password"
            value={form.confirm}
            onChange={update('confirm')}
            aria-invalid={mismatch}
            required
          />
          {mismatch && <span className="field-hint bad">Passwords do not match</span>}
        </label>

        {error && <p className="form-error" role="alert">{error}</p>}

        <button
          type="submit"
          className="btn btn-pink btn-block"
          disabled={
            submitting ||
            !form.first_name.trim() ||
            !form.last_name.trim() ||
            !form.email.trim() ||
            !form.password ||
            !form.confirm
          }
        >
          {submitting ? 'Creating account…' : 'Create Account'}
        </button>

        <p className="muted small">
          Already have an account? <Link to="/login" className="pink">Log in</Link>
        </p>
      </form>
    </section>
  )
}
