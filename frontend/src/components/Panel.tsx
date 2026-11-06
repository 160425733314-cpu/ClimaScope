import type { ReactNode } from "react";
export function Panel({ title, eyebrow, children, className = "" }: { title?: string; eyebrow?: string; children: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}>{eyebrow && <div className="eyebrow">{eyebrow}</div>}{title && <h2>{title}</h2>}{children}</section>;
}
