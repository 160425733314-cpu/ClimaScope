import type { Risk } from "../types";
export function RiskCard({ risk }: { risk: Risk }) {
  return <div className={`risk-card risk-${risk.level.toLowerCase()}`}><div className="risk-top"><div><span className="eyebrow">COMPOUND RISK SCREENING</span><h2>{risk.level}</h2></div><div className="risk-score">{Math.round(risk.score)}<small>/100</small></div></div><p>{risk.headline}</p><div className="progress"><i style={{ width: `${risk.score}%` }} /></div><div className="risk-meta"><span>{risk.completeness}% data completeness</span><span>{risk.uncertainty}</span></div></div>;
}
