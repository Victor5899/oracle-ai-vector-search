import BrandMark from './BrandMark'
import StatusIndicator from './StatusIndicator'

const NAV_LINKS = [
  { href: '#documents', label: 'Documents' },
  { href: '#ask', label: 'Ask' },
]

export default function AppHeader({ health }) {
  return (
    <header className="header">
      <div className="header__inner">
        <a className="brand" href="#ask">
          <span className="brand__badge">
            <BrandMark />
          </span>
          <span className="brand__text">
            <span className="brand__name">Oracle AI Vector Search</span>
            <span className="brand__subtitle">Smart Document Q&amp;A</span>
          </span>
        </a>

        <nav className="header__nav" aria-label="Sections">
          {NAV_LINKS.map((link) => (
            <a key={link.href} className="nav-link" href={link.href}>
              {link.label}
            </a>
          ))}
        </nav>

        <StatusIndicator
          state={health.state}
          descriptor={health.descriptor}
          onRefresh={health.refresh}
        />
      </div>
    </header>
  )
}
