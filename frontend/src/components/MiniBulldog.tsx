import Bulldog from './Bulldog'

// The HTML/CSS mascot shrunk to an avatar (chat bubbles, chat button).
export default function MiniBulldog({ size = 36 }: { size?: number }) {
  return (
    <span className="mini-dog" style={{ width: size, height: size, ['--s' as string]: size / 300 }} aria-hidden="true">
      <Bulldog />
    </span>
  )
}
