import { useEffect, useState } from "react";
import { Activity, BrainCircuit, Building2, ChevronRight, Database, Gauge, MapPinned, Menu, Play, ShieldAlert, Wind, X } from "lucide-react";
import { getDashboard } from "./services/api";
import type { Dashboard } from "./types";
import { CommandCenter } from "./pages/CommandCenter";
import { Intelligence } from "./pages/Intelligence";
import { Simulator } from "./pages/Simulator";
import { Transparency } from "./pages/Transparency";
import { OperationalPage } from "./pages/OperationalPage";

const nav = [{ id: "command", label: "Command Center", icon: Gauge }, { id: "twin", label: "Urban Digital Twin", icon: MapPinned }, { id: "risk", label: "Compound Risk Intelligence", icon: ShieldAlert }, { id: "sim", label: "What-If Simulator", icon: Play }, { id: "predictive", label: "Predictive Intelligence", icon: BrainCircuit }, { id: "air", label: "Air Quality Intelligence", icon: Wind }, { id: "history", label: "Historical Analysis", icon: Activity }, { id: "cities", label: "Multi-City Monitor", icon: Building2 }, { id: "transparency", label: "Data & Transparency", icon: Database }];
export default function App() { const [city, setCity] = useState("Hyderabad"); const [input, setInput] = useState("Hyderabad"); const [page, setPage] = useState("command"); const [data, setData] = useState<Dashboard | null>(null); const [error, setError] = useState(""); const [mobile, setMobile] = useState(false);
  async function load(next = city) { setError(""); try { setData(await getDashboard(next)); } catch (e) { setError(e instanceof Error ? e.message : "Unable to load data"); } }
  useEffect(() => { load(); }, []);
  function navigate(id: string) { setPage(id); setMobile(false); }
  const render = data && (page === "risk" ? <Intelligence data={data} /> : page === "sim" ? <Simulator data={data} /> : page === "transparency" ? <Transparency data={data} /> : page === "command" ? <CommandCenter data={data} /> : <OperationalPage kind={page} data={data} />);
  return <div className="app-shell"><aside className={mobile ? "sidebar open" : "sidebar"}><div className="brand"><div className="brand-mark">C</div><div><strong>CliMA<span>Scope</span></strong><small>URBAN CLIMATE INTELLIGENCE</small></div><button className="close-mobile" onClick={() => setMobile(false)}><X size={18} /></button></div><nav>{nav.map(item => { const Icon = item.icon; return <button key={item.id} className={page === item.id ? "active" : ""} onClick={() => navigate(item.id)}><Icon size={17} />{item.label}{page === item.id && <ChevronRight size={14} className="nav-arrow" />}</button>; })}</nav><div className="sidebar-foot"><span className="status-dot" /> Data services operational<br /><small>Model v1.0 · heuristic screening</small></div></aside><main className="main"><header><button className="menu" onClick={() => setMobile(true)}><Menu size={20} /></button><div className="search"><span>LOCATION</span><input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === "Enter" && (setCity(input), load(input))} /><button onClick={() => { setCity(input); load(input); }}>Analyse</button></div><div className="header-right"><span className="live"><i /> Live model feeds</span></div></header>{error && <div className="error">{error}<button onClick={() => load()}>Retry</button></div>}{!data && !error && <div className="loading"><div className="spinner" />Loading climate intelligence…</div>}{render}</main></div>;
}
