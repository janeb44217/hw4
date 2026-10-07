// The Campus Customs bulldog mascot, drawn with HTML + CSS.
export default function Bulldog() {
  return (
    <div className="bulldog" aria-hidden="true">
      <div className="bd-ear left" />
      <div className="bd-ear right" />
      <div className="bd-head">
        <div className="bd-brow left" />
        <div className="bd-brow right" />
        <div className="bd-eye left" />
        <div className="bd-eye right" />
        <div className="bd-muzzle">
          <div className="bd-nose" />
          <div className="bd-mouth" />
          <div className="bd-tooth left" />
          <div className="bd-tooth right" />
        </div>
        <div className="bd-cheek left" />
        <div className="bd-cheek right" />
      </div>
      <div className="bd-sweater">
        <span className="bd-sweater-y">Y</span>
        <span className="bd-stripe" />
      </div>
      <div className="bd-collar">
        <span className="bd-tag">CC</span>
      </div>
    </div>
  )
}
