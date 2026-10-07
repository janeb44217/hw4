// Scrolling "stadium ticker" under the nav. Content is duplicated so the loop is seamless.
const ITEMS = [
  'Boola Boola',
  'Officially licensed Yale apparel',
  'Visit us at 57 Broadway, New Haven',
  'Ask the Bulldog Assistant about sizes & stock',
  'Beat Harvard',
  'Hoodies · Crewnecks · Quarter-zips · Tees',
]

export default function Marquee() {
  const row = ITEMS.map((t) => (
    <span className="marquee-item" key={t}>
      {t}
      <span className="marquee-star" aria-hidden="true">✦</span>
    </span>
  ))
  return (
    <div className="marquee" aria-label="Campus Customs highlights">
      <div className="marquee-track">
        <div className="marquee-row">{row}</div>
        <div className="marquee-row" aria-hidden="true">{row}</div>
      </div>
    </div>
  )
}
