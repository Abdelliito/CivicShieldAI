import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Circle, CircleMarker, MapContainer, Popup, TileLayer, Tooltip, useMap, useMapEvents } from "react-leaflet";
import { latLng, latLngBounds, type Circle as LeafletCircle, type CircleMarker as LeafletMarker, type Map as LeafletMap } from "leaflet";
import { ArrowRight, LocateFixed, MapPin, X } from "lucide-react";
import type { Incident, Risk } from "../lib/types";
import { SEVERITIES } from "../lib/types";
import { Badge } from "./UI";
import "leaflet/dist/leaflet.css";

const colors: Record<string, string> = {
  Critical: "#B94A43", High: "#D49A43", Moderate: "#D49A43",
  Medium: "#85724F", Low: "#34765D", "Insufficient Data": "#7A8580",
};
const emptyIncidents: Incident[] = [];
const emptyRisks: Risk[] = [];

function Picker({ onPick }: { onPick: (lat: number, lng: number) => void }) {
  useMapEvents({ click: (event) => onPick(event.latlng.lat, event.latlng.lng) });
  return null;
}

function Recenter({ latitude, longitude }: { latitude: number; longitude: number }) {
  const map = useMap();
  useEffect(() => { map.panTo([latitude, longitude], { animate: false }); }, [map, latitude, longitude]);
  return null;
}

function IncidentMarker({ incident, selected, onSelect }: {
  incident: Incident; selected: boolean; onSelect: (incident: Incident) => void;
}) {
  const marker = useRef<LeafletMarker>(null);
  useEffect(() => {
    const element = marker.current?.getElement();
    if (!element) return;
    element.setAttribute("role", "button");
    element.setAttribute("tabindex", "0");
    element.setAttribute("aria-label", `Select incident ${incident.reference}`);
    element.setAttribute("aria-pressed", String(selected));
    const keydown = (event: Event) => {
      if (event instanceof KeyboardEvent && (event.key === "Enter" || event.key === " ")) {
        event.preventDefault();
        event.stopPropagation();
        onSelect(incident);
      }
    };
    element.addEventListener("keydown", keydown);
    return () => element.removeEventListener("keydown", keydown);
  }, [incident, onSelect, selected]);
  return (
    <CircleMarker
      ref={marker}
      center={[incident.latitude, incident.longitude]}
      radius={selected ? 11 : incident.severity === "Critical" ? 8 : 6}
      pathOptions={{ className: "civic-incident-marker", color: selected ? "#202A29" : "#FFFFFF", weight: selected ? 3 : 2, fillColor: colors[incident.severity] || colors.Low, fillOpacity: 1 }}
      eventHandlers={{ click: () => onSelect(incident) }}
    >
      <Tooltip direction="top" offset={[0, -8]}>
        <strong>{incident.reference}</strong><br />{incident.category} · {incident.severity}
      </Tooltip>
    </CircleMarker>
  );
}

function RiskZone({ risk, onRisk }: { risk: Risk; onRisk?: (risk: Risk) => void }) {
  const zone = useRef<LeafletCircle>(null);
  const activate = useCallback(() => onRisk ? onRisk(risk) : zone.current?.openPopup(), [onRisk, risk]);
  useEffect(() => {
    const element = zone.current?.getElement();
    if (!element) return;
    element.setAttribute("role", "button");
    element.setAttribute("tabindex", "0");
    element.setAttribute("aria-label", `Inspect risk zone ${risk.zone_name}`);
    const keydown = (event: Event) => {
      if (event instanceof KeyboardEvent && (event.key === "Enter" || event.key === " ")) {
        event.preventDefault(); event.stopPropagation(); activate();
      }
    };
    element.addEventListener("keydown", keydown);
    return () => element.removeEventListener("keydown", keydown);
  }, [risk.zone_name, activate]);
  return <Circle ref={zone} center={[risk.latitude, risk.longitude]} radius={risk.radius_km * 1000}
    pathOptions={{ className: "civic-risk-zone", color: colors[risk.level] || colors["Insufficient Data"], weight: 1.5, fillOpacity: 0.045, dashArray: "5 5" }}
    eventHandlers={{ click: activate }}>
    <Tooltip sticky>{risk.zone_name} · {risk.level} · {risk.score ?? "N/A"}/100</Tooltip>
    {!onRisk && <Popup><strong>{risk.zone_name}</strong><p>Risk estimate: {risk.score ?? "N/A"} / 100</p><Badge>{risk.level}</Badge></Popup>}
  </Circle>;
}

export function CivicMap({ incidents = emptyIncidents, risks = emptyRisks, height = 360, onIncident, onRisk, picker, controls = true }: {
  incidents?: Incident[]; risks?: Risk[]; height?: number;
  onIncident?: (id: number) => void; onRisk?: (risk: Risk) => void;
  controls?: boolean;
  picker?: { latitude: number; longitude: number; onPick: (lat: number, lng: number) => void };
}) {
  const [map, setMap] = useState<LeafletMap | null>(null);
  const [incidentLayer, setIncidentLayer] = useState(true);
  const [riskLayer, setRiskLayer] = useState(true);
  const [severity, setSeverity] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const fittedView = useRef<{ map: LeafletMap; extent: string } | null>(null);
  const located = useMemo(() => incidents.filter((i) => Number.isFinite(i.latitude) && Number.isFinite(i.longitude)), [incidents]);
  const selected = located.find((incident) => incident.id === selectedId);
  const selectIncident = useCallback((incident: Incident) => setSelectedId(incident.id), []);
  const bounds = useMemo(() => {
    const result = latLngBounds([]);
    located.forEach((i) => result.extend([i.latitude, i.longitude]));
    risks.forEach((r) => result.extend(latLng(r.latitude, r.longitude).toBounds(r.radius_km * 2000)));
    return result;
  }, [located, risks]);
  const extent = bounds.isValid() ? bounds.toBBoxString() : "Lahore";
  function focusLahore() {
    if (!map) return;
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [32, 52], maxZoom: 13, animate: false });
    else map.setView([31.5204, 74.3382], 12, { animate: false });
  }
  useEffect(() => {
    if (!map || picker) return;
    if (fittedView.current?.map === map && fittedView.current.extent === extent) return;
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [32, 52], maxZoom: 13, animate: false });
    else map.setView([31.5204, 74.3382], 12, { animate: false });
    fittedView.current = { map, extent };
  }, [map, bounds, picker, extent]);
  useEffect(() => {
    if (!map) return;
    // Leaflet must measure again when responsive grid columns or a dialog change size.
    const observer = new ResizeObserver(() => map.invalidateSize({ animate: false }));
    observer.observe(map.getContainer());
    return () => observer.disconnect();
  }, [map]);
  const selectedVisible = selected && incidentLayer && (!severity || selected.severity === severity);
  return (
    <div className={`civic-map-shell${picker ? " civic-map-picker" : ""}`} style={{ height }}>
      <MapContainer
        ref={setMap}
        center={[picker?.latitude ?? 31.5204, picker?.longitude ?? 74.3382]}
        zoom={picker ? 13 : 12}
        zoomSnap={0.25}
        zoomAnimation={false}
        style={{ height: "100%", width: "100%" }}
        scrollWheelZoom={false}
        attributionControl
      >
        <TileLayer url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' />
        {!picker && riskLayer && risks.map((risk) => <RiskZone key={risk.id} risk={risk} onRisk={onRisk} />)}
        {!picker && incidentLayer && located.filter((i) => !severity || i.severity === severity).map((incident) => (
          <IncidentMarker key={incident.id} incident={incident} selected={selected?.id === incident.id} onSelect={selectIncident} />
        ))}
        {picker && <>
          <Picker onPick={picker.onPick} />
          <Recenter latitude={picker.latitude} longitude={picker.longitude} />
          <CircleMarker center={[picker.latitude, picker.longitude]} radius={9} pathOptions={{ color: "#fff", weight: 3, fillColor: "#285E51", fillOpacity: 1 }} />
        </>}
      </MapContainer>
      {!picker && controls && <>
        <div className="civic-map-toolbar">
          <div className="civic-map-layers">
            <label><input type="checkbox" aria-label="Incident layer" checked={incidentLayer} onChange={(e) => setIncidentLayer(e.target.checked)} />Incidents</label>
            <label><input type="checkbox" aria-label="Flood-risk layer" checked={riskLayer} onChange={(e) => setRiskLayer(e.target.checked)} />Flood risk</label>
            <select aria-label="Map severity filter" value={severity} onChange={(e) => setSeverity(e.target.value)}>
              <option value="">All severities</option>
              {SEVERITIES.map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
          <button type="button" className="civic-map-focus" onClick={focusLahore} aria-label="Focus Lahore"><LocateFixed size={15} /><span>Focus Lahore</span></button>
        </div>
        {selectedVisible && <section className="civic-map-context" role="region" aria-label="Selected incident">
          <div className="section-line"><span className="mono">{selected.reference}</span><button type="button" className="icon-button" aria-label="Clear map selection" onClick={() => setSelectedId(null)}><X size={15} /></button></div>
          <strong>{selected.title}</strong>
          <small className="muted block">{selected.category}</small>
          <p><MapPin size={12} />{selected.location_name}</p>
          <div className="inline-badges"><Badge>{selected.severity}</Badge><Badge>{selected.status}</Badge></div>
          {onIncident && <button type="button" className="text-link" onClick={() => onIncident(selected.id)}>Open incident details <ArrowRight size={14} /></button>}
        </section>}
        <div className="civic-map-legend" aria-label="Incident severity legend">
          {["Critical", "High", "Medium", "Low"].map((level) => <span key={level}><i style={{ background: colors[level] }} />{level}</span>)}
        </div>
      </>}
    </div>
  );
}
