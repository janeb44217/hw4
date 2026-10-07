import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

const mainLinks = [
  { to: '/', label: 'Home' },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

export default function NavBar() {
  const [open, setOpen] = useState(false)
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const close = () => setOpen(false)

  async function handleLogout() {
    close()
    await logout()
    navigate('/')
  }
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    isActive ? 'nav-link active' : 'nav-link'

  return (
    <header className="navbar">
      <div className="navbar-inner">
        <Link to="/" className="brand" onClick={close}>
          <span className="brand-patch" aria-hidden="true">CC</span>
          <span className="brand-name">
            Campus <span className="pink">Customs</span>
            <span className="brand-sub">Yale apparel · New Haven</span>
          </span>
        </Link>

        <button
          className="nav-toggle"
          aria-label="Toggle navigation"
          aria-expanded={open}
          onClick={() => setOpen(!open)}
        >
          <span />
          <span />
          <span />
        </button>

        <nav className={open ? 'nav open' : 'nav'}>
          <ul className="nav-main">
            {mainLinks.map((l) => (
              <li key={l.to}>
                <NavLink to={l.to} end={l.to === '/'} className={linkClass} onClick={close}>
                  {l.label}
                </NavLink>
              </li>
            ))}
          </ul>
          <ul className="nav-account">
            {user ? (
              <>
                <li className="nav-greeting">
                  Hi, <span className="pink">{user.first_name}</span>
                </li>
                <li>
                  <button className="btn btn-outline btn-sm" onClick={handleLogout}>
                    Log Out
                  </button>
                </li>
              </>
            ) : (
              <>
                <li>
                  <NavLink to="/login" className={linkClass} onClick={close}>
                    Log In
                  </NavLink>
                </li>
                <li>
                  <NavLink to="/create-account" className="btn btn-pink btn-sm" onClick={close}>
                    Create Account
                  </NavLink>
                </li>
              </>
            )}
          </ul>
        </nav>
      </div>
    </header>
  )
}
