// A felt pennant with stitched edge, drawn in HTML/CSS.
export default function Pennant({ text, className = '' }: { text: string; className?: string }) {
  return (
    <div className={`pennant ${className}`} aria-hidden="true">
      <span className="pennant-pole" />
      <span className="pennant-flag">
        <span className="pennant-text">{text}</span>
      </span>
    </div>
  )
}
