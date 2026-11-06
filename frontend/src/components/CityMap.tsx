import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import type { Location, Risk } from "../types";

export function CityMap({ location, risk }: { location: Location; risk: Risk }) {
  return <div className="map-wrap"><MapContainer center={[location.latitude, location.longitude]} zoom={8} scrollWheelZoom className="map"><TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" /><CircleMarker center={[location.latitude, location.longitude]} radius={14} pathOptions={{ color: risk.level === "Severe" ? "#ff5b67" : risk.level === "High" ? "#ffad5c" : "#32d2d1", fillOpacity: 0.75 }}><Popup><strong>{location.name}</strong><br />Compound risk: {risk.level} ({Math.round(risk.score)}/100)<br />City-level model grid; not street-level data.</Popup></CircleMarker></MapContainer><div className="map-legend"><span><i className="dot dot-low" /> Low</span><span><i className="dot dot-mod" /> Moderate</span><span><i className="dot dot-high" /> High / severe</span></div></div>;
}
