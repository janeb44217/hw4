import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <div>
          <p className="brand-name">
            Campus <span className="pink">Customs</span>
          </p>
          <p className="muted">Officially licensed Yale apparel for every Bulldog.</p>
        </div>
        <div>
          <p className="footer-heading">Visit</p>
          <p className="muted">57 Broadway, New Haven, CT 06511</p>
        </div>
        <div>
          <p className="footer-heading">Explore</p>
          <Link to="/products">Products</Link>
          <Link to="/about">About Us</Link>
          <Link to="/create-account">Create Account</Link>
        </div>
      </div>
      <p className="footer-legal muted">© {new Date().getFullYear()} Campus Customs. Boola Boola.</p>
    </footer>
  )
}
