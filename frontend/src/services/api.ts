import type { Dashboard, Risk } from "../types";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
export async function getDashboard(city: string): Promise<Dashboard> {
  const response = await fetch(`${API}/api/dashboard?city=${encodeURIComponent(city)}`);
  if (!response.ok) throw new Error((await response.json()).detail || "Unable to load climate data");
  return response.json();
}
export async function getScenario(observation: Record<string, unknown>, changes: Record<string, unknown>) {
  const response = await fetch(`${API}/api/risk/scenario`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ observation, changes }) });
  if (!response.ok) throw new Error("Scenario calculation failed");
  return response.json() as Promise<{ baseline: Risk; scenario: Risk; delta: number; assumptions: string[] }>;
}
