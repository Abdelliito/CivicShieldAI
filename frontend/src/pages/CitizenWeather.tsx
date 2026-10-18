import { createContext, useContext, useState } from "react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Cloud, CloudLightning, CloudRain, CloudSun, Droplets, LocateFixed, MapPin, Snowflake, Sun, TriangleAlert, Wind, ArrowRight } from "lucide-react";
import { date, useApi } from "../lib/api";
import type { Json } from "../lib/types";
import { Badge, Button, Field, Loading, Modal } from "../components/UI";
import { CivicMap } from "../components/Map";

type LocalArea = { latitude: number; longitude: number; label: string };
const DEFAULT_AREA: LocalArea = { latitude: 31.5204, longitude: 74.3587, label: "Lahore · default area" };
const AreaContext = createContext<{ area: LocalArea; setArea: (area: LocalArea) => void }>({ area: DEFAULT_AREA, setArea: () => {} });
export function WeatherLocationProvider({ children }: { children: ReactNode }) {
  const [area, updateArea] = useState<LocalArea>(() => {
    try {
      const saved = JSON.parse(localStorage.getItem("civicshield.weather-area.v1") || "null");
      return saved && Number.isFinite(saved.latitude) && Number.isFinite(saved.longitude) && Math.abs(saved.latitude) <= 90 && Math.abs(saved.longitude) <= 180 && typeof saved.label === "string" ? saved : DEFAULT_AREA;
    } catch { return DEFAULT_AREA; }
  });
  function setArea(value: LocalArea) { updateArea(value); localStorage.setItem("civicshield.weather-area.v1", JSON.stringify(value)); }
  return <AreaContext.Provider value={{ area, setArea }}>{children}</AreaContext.Provider>;
}
function useConditions() {
  const { area } = useContext(AreaContext);
  const query = `latitude=${area.latitude}&longitude=${area.longitude}`;
  return { area, weather: useApi<Json>(`/citizen/weather?${query}`), alerts: useApi<Json>(`/citizen/alerts?${query}`) };
}
export function WeatherIcon({ code, size = 30 }: { code?: number; size?: number }) {
  const Icon = code == null ? Cloud : code === 0 ? Sun : code < 4 ? CloudSun : code >= 95 ? CloudLightning : code >= 71 && code <= 77 ? Snowflake : code >= 51 ? CloudRain : Cloud;
  return <Icon size={size} strokeWidth={1.5} aria-hidden="true" />;
}
function number(value: unknown, suffix = "") { return typeof value === "number" && Number.isFinite(value) ? `${Math.round(value)}${suffix}` : "Unavailable"; }
export function AreaSelector() {
  const { area, setArea } = useContext(AreaContext);
  const [open, setOpen] = useState(false), [latitude, setLatitude] = useState(String(area.latitude)), [longitude, setLongitude] = useState(String(area.longitude)), [label, setLabel] = useState(""), [gps, setGps] = useState(false), [error, setError] = useState("");
  function locate() {
    if (!navigator.geolocation) { setError("Location is unavailable. Choose a point on the map instead."); return; }
    setGps(true); setError("");
    navigator.geolocation.getCurrentPosition((point) => {
      setArea({ latitude: point.coords.latitude, longitude: point.coords.longitude, label: "Your selected current location" }); setGps(false);
    }, () => { setGps(false); setError("Location permission was unavailable. Use Change area to select a map point or coordinates."); }, { timeout: 12000, maximumAge: 60000 });
  }
  function save() {
    const lat = Number(latitude), lng = Number(longitude);
    if (!latitude.trim() || !longitude.trim() || !Number.isFinite(lat) || !Number.isFinite(lng) || Math.abs(lat) > 90 || Math.abs(lng) > 180) { setError("Enter valid latitude and longitude or select a point on the map."); return; }
    setArea({ latitude: lat, longitude: lng, label: label.trim() || `Selected area · ${lat.toFixed(3)}, ${lng.toFixed(3)}` }); setOpen(false); setError("");
  }
  return <div className="weather-area-selector"><div><MapPin size={17} /><span>{area.label}</span></div><div className="inline-actions"><Button className="button-secondary small" pending={gps} onClick={locate}><LocateFixed size={14} />Use my location</Button><Button className="button-ghost small" onClick={() => { setLatitude(String(area.latitude)); setLongitude(String(area.longitude)); setError(""); setOpen(true); }}>Change area</Button></div>{error && !open && <p className="form-error" role="alert">{error}</p>}{open && <Modal open onClose={() => setOpen(false)} title="Choose your weather area" description="Select the area you want to check. Weather forecasts are estimates for these coordinates." wide><form className="stack" onSubmit={(event) => { event.preventDefault(); save(); }}><CivicMap height={260} picker={{ latitude: Number(latitude) || area.latitude, longitude: Number(longitude) || area.longitude, onPick: (lat, lng) => { setLatitude(lat.toFixed(6)); setLongitude(lng.toFixed(6)); } }} /><div className="form-grid"><Field label="Area latitude"><input type="number" step="any" min={-90} max={90} required value={latitude} onChange={(event) => setLatitude(event.target.value)} /></Field><Field label="Area longitude"><input type="number" step="any" min={-180} max={180} required value={longitude} onChange={(event) => setLongitude(event.target.value)} /></Field></div><Field label="Area name (optional)"><input value={label} maxLength={120} placeholder="Your neighbourhood" onChange={(event) => setLabel(event.target.value)} /></Field>{error && <p role="alert" className="form-error">{error}</p>}<Button type="submit">Check this area</Button></form></Modal>}</div>;
}
function ForecastUnavailable({ message, retry }: { message?: string; retry: () => void }) {
  return <div className="weather-unavailable"><Cloud size={29} /><div><h3>Weather is unavailable right now</h3><p>{message || "The weather service did not return current data. Please try again later."}</p><Button className="button-ghost small" onClick={retry}>Try again</Button></div></div>;
}
export function CitizenConditionsSummary() {
  const { weather, alerts } = useConditions();
  const current = weather.data?.current || {}, risk = [...(alerts.data?.risks || []), ...(alerts.data?.weather_precautions || [])][0];
  return <div className="citizen-conditions-summary"><section className="panel compact-weather"><div className="panel-heading"><h2>Weather near you</h2><Link to="/weather">7-day forecast <ArrowRight size={14} /></Link></div>{weather.isLoading ? <p className="conditions-pending">Checking the weather…</p> : weather.isError || weather.data?.available === false ? <p className="conditions-pending">Weather is unavailable. <Link to="/weather">Check your area</Link></p> : <div className="compact-condition"><WeatherIcon code={current.weather_code} size={39} /><strong>{number(current.temperature_2m, "°")}</strong><div><p>{current.condition || "Current conditions"}</p><small>Humidity {number(current.relative_humidity_2m, "%")} · Wind {number(current.wind_speed_10m, " km/h")}</small></div></div>}<p className="weather-summary-source">{weather.data?.source || "Open-Meteo"} · <Link to="/weather">Choose your area</Link></p></section><section className="panel compact-alert"><div className="panel-heading"><h2>Disaster alerts & predictions</h2><Link to="/alerts">View advice <ArrowRight size={14} /></Link></div><div className="compact-alert-body"><TriangleAlert size={25} /><div><strong>{risk ? `${risk.type}: ${risk.level}` : alerts.isLoading ? "Checking available area information…" : "Check the available risk information"}</strong><p>{risk?.summary || "Choose your area to see planning estimates and weather-based precautions."}</p></div></div><p className="weather-summary-source">Planning estimates · no official warning feed connected</p></section></div>;
}
export function CitizenWeather() {
  const { weather } = useConditions(), data = weather.data, current = data?.current || {};
  return <div className="citizen-weather-page"><AreaSelector />{weather.isLoading ? <Loading text="Checking local weather…" /> : weather.isError || data?.available === false ? <ForecastUnavailable message={weather.error?.message || data?.message} retry={() => void weather.refetch()} /> : <><section className="current-weather panel"><div className="current-weather-main"><WeatherIcon code={current.weather_code} size={69} /><div><p>Current weather</p><strong>{number(current.temperature_2m, "°C")}</strong><h2>{current.condition || "Current conditions"}</h2></div></div><dl className="weather-measures"><div><Droplets size={19} /><dt>Humidity</dt><dd>{number(current.relative_humidity_2m, "%")}</dd></div><div><Wind size={19} /><dt>Wind speed</dt><dd>{number(current.wind_speed_10m, " km/h")}</dd></div><div><CloudRain size={19} /><dt>Rain chance today</dt><dd>{number(data?.daily?.[0]?.rain_probability, "%")}</dd></div></dl><p className="weather-provenance">{data?.source || "Open-Meteo"} · Updated {date(data?.updated_at)} · Timezone: {data?.timezone || "See forecast source"}. Forecasts can change.</p></section><section className="panel weekly-weather"><div className="panel-heading"><div><h2>Your next 7 days</h2><p>Daily highs, lows and the chance of rain</p></div></div><div className="forecast-days">{(data?.daily || []).map((day: Json, index: number) => <article className="forecast-day" key={day.date}><h3>{index === 0 ? "Today" : new Date(`${day.date}T12:00:00`).toLocaleDateString("en-GB", { weekday: "short" })}</h3><time dateTime={day.date}>{new Date(`${day.date}T12:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}</time><WeatherIcon code={day.weather_code} size={31} /><p>{day.condition || "Forecast"}</p><strong>{number(day.temperature_max, "°")} <span>{number(day.temperature_min, "°")}</span></strong><small><CloudRain size={13} />{number(day.rain_probability, "%")} rain</small><small>{number(day.precipitation_mm, " mm")}</small></article>)}</div>{!data?.daily?.length && <p className="conditions-pending">A daily forecast is not available for this area.</p>}</section></>}<p className="citizen-data-note">Weather comes from a forecast service. It is separate from the civic report image analysis and is not generated by an AI language model. <Link to="/alerts">View local risk advice</Link>.</p></div>;
}
export function CitizenAlerts() {
  const { alerts } = useConditions(), data = alerts.data;
  const risks: Json[] = [...(data?.risks || []), ...(data?.weather_precautions || [])];
  return <div className="citizen-alerts-page"><AreaSelector /><div className="alerts-source-notice"><TriangleAlert size={21} /><div><strong>Planning advice, with its source shown</strong><p>{data?.official_alerts_message || "No official warning feed is connected."} These are local risk estimates and weather-based precautions. They are not confirmed disaster predictions or emergency instructions.</p></div></div>{alerts.isLoading ? <Loading text="Checking available risks and precautions…" /> : alerts.isError ? <ForecastUnavailable message={alerts.error.message} retry={() => void alerts.refetch()} /> : <><section className="alert-area-summary"><h2>{data?.area?.name || "Your selected area"}</h2><p>{data?.message || "Review what might happen, when the estimate applies, and what you can do."}</p>{data?.issued_at && <small>Checked {date(data.issued_at)}</small>}</section><div className="citizen-risk-list">{risks.map((risk, index) => <article className={`panel citizen-risk-card risk-${String(risk.level).toLowerCase().replaceAll(" ", "-")}`} key={`${risk.id || risk.type}-${index}`}><div className="citizen-risk-heading"><div><TriangleAlert size={23} /><h2>{risk.type}</h2></div><Badge>{risk.level}</Badge></div><p className="risk-plain-summary">{risk.summary}</p><div className="risk-timing"><span>Issued {date(risk.issued_at || data?.issued_at)}</span>{risk.valid_until && <span>Applies until {date(risk.valid_until)}</span>}</div><h3>What you can do</h3><ul>{risk.precautions?.map((advice: string, adviceIndex: number) => <li key={adviceIndex}>{advice}</li>)}</ul><p className="risk-plain-source">{risk.is_demo ? "Demonstration inputs · " : ""}{risk.source || "Source unavailable"} · {risk.official ? "Official source" : "Estimate / general precautions"}</p>{risk.details && <details className="plain-risk-details"><summary>How this estimate was made</summary>{risk.details.factors?.explanation && <p>{risk.details.factors.explanation}</p>}<p>{risk.details.score == null ? "There is not enough information for a numerical estimate." : `Planning score: ${risk.details.score}/100. This is not a probability of flooding.`}</p></details>}</article>)}</div>{!risks.length && <div className="panel no-risk-information"><h3>No current risk information is available for this area</h3><p>This does not confirm the area is safe. Check local official sources and try another area or refresh later.</p><Button className="button-secondary" onClick={() => void alerts.refetch()}>Check again</Button></div>}</>}<p className="citizen-data-note">If you see an immediate threat, move to safety and contact the appropriate local emergency service. CivicShield does not dispatch emergency crews.</p></div>;
}
