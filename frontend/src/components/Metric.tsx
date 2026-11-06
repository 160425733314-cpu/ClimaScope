export function Metric({ label, value, note, tone = "cyan" }: { label: string; value: string; note?: string; tone?: string }) {
  return <div className={`metric metric-${tone}`}><span>{label}</span><strong>{value}</strong>{note && <small>{note}</small>}</div>;
}
