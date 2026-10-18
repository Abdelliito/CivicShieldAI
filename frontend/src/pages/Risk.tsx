import { useState } from "react";
import { CloudRain, History, RefreshCw, Waves } from "lucide-react";
import { api, date, json, useAction, useApi } from "../lib/api";
import type { Incident, Json, Risk as RiskType } from "../lib/types";
import {
  Badge,
  Button,
  Empty,
  ErrorState,
  Loading,
  Modal,
} from "../components/UI";
import { CivicMap } from "../components/Map";
import {
  RiskFactors,
  ProvenanceSummary,
} from "../components/IntelligenceSummary";
export function Risk() {
  const risks = useApi<RiskType[]>("/risk"),
    weather = useApi<Json[]>("/weather"),
    incidents = useApi<Incident[]>("/incidents");
  const [scenario, setScenario] = useState(""),
    [selectedZoneId, setSelectedZoneId] = useState<number | null>(null);
  const selected = risks.data?.find((risk) => risk.zone_id === selectedZoneId);
  const refresh = useAction(
    () =>
      api("/risk/refresh", {
        method: "POST",
        body: json(scenario ? { scenario } : {}),
      }),
    "Risk assessments recalculated",
  );
  const snapshots = Array.isArray(weather.data)
    ? weather.data
    : weather.data
      ? [weather.data]
      : [];
  return (
    <>
      <div className="risk-toolbar">
        <div>
          <CloudRain size={22} />
          <span>Local flooding & waterlogging estimates</span>
        </div>
        <div className="inline-controls">
          <select
            aria-label="Weather scenario"
            value={scenario}
            onChange={(e) => setScenario(e.target.value)}
          >
            <option value="">Live weather refresh</option>
            <option value="heavy_rain">Demo · heavy rainfall</option>
            <option value="clear">Demo · clear weather</option>
            <option value="missing">Demo · missing weather</option>
          </select>
          <Button
            pending={refresh.isPending}
            onClick={() => refresh.mutate(undefined)}
          >
            <RefreshCw size={15} />
            Refresh weather & risk
          </Button>
        </div>
      </div>
      <p className="notice">
        Risk scores are transparent estimates, not disaster probabilities.
        Synthetic historical inputs and simulated weather are identified in each
        assessment.
      </p>
      {risks.isLoading ? (
        <Loading />
      ) : risks.error ? (
        <ErrorState error={risks.error} retry={() => void risks.refetch()} />
      ) : (
        <div className="risk-layout">
          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>Flood-risk map</h2>
                <p>Inspect zones and reported hazards</p>
              </div>
              <Waves size={20} className="teal" />
            </div>
            <CivicMap
              incidents={incidents.data || []}
              risks={risks.data || []}
              height={460}
              onRisk={(risk) => setSelectedZoneId(risk.zone_id)}
            />
            <div className="map-legend">
              <span>
                <i className="dot teal" />
                Low
              </span>
              <span>
                <i className="dot amber" />
                Moderate
              </span>
              <span>
                <i className="dot coral" />
                High
              </span>
              <span>
                <i className="dot gray" />
                Insufficient data
              </span>
            </div>
          </section>
          <section className="panel risk-zones">
            <div className="panel-heading">
              <h2>Zone assessments</h2>
              <span className="muted">{risks.data?.length || 0} zones</span>
            </div>
            {risks.data?.length ? (
              risks.data.map((risk) => (
                <button
                  key={risk.id}
                  className="zone-row"
                  onClick={() => setSelectedZoneId(risk.zone_id)}
                  aria-label={`Inspect ${risk.zone_name}`}
                >
                  <div className="section-line">
                    <strong>{risk.zone_name}</strong>
                    <Badge>{risk.level}</Badge>
                  </div>
                  <div className="zone-score">
                    <strong>
                      {risk.score == null ? "—" : Math.round(risk.score)}
                      <small>/100</small>
                    </strong>
                    <div className="score-track">
                      <i
                        style={{ width: `${risk.score || 0}%` }}
                        className={risk.level.toLowerCase()}
                      />
                    </div>
                  </div>
                  <small>Calculated {date(risk.created_at)}</small>
                </button>
              ))
            ) : (
              <Empty
                title="No risk calculations yet"
                body="Refresh weather & risk to calculate zone estimates."
              />
            )}
          </section>
        </div>
      )}
      <section className="panel weather-panel">
        <div className="panel-heading">
          <h2>Weather inputs</h2>
          <span className="muted">Most recent stored observations</span>
        </div>
        <div className="weather-list">
          {snapshots.slice(0, 8).map((w, index) => (
            <div className="weather-item" key={w.id || index}>
              <div className="section-line">
                <strong>
                  {w.zone_name || `Zone ${w.zone_id || "Lahore"}`}
                </strong>
                <Badge>
                  {w.error
                    ? "Unavailable"
                    : w.is_demo
                      ? "Demo input"
                      : "Live source"}
                </Badge>
              </div>
              <div className="weather-values">
                <div>
                  <strong>
                    {w.rainfall_mm ?? "—"}
                    <small>mm</small>
                  </strong>
                  <span>Recent rainfall</span>
                </div>
                <div>
                  <strong>
                    {w.forecast_rainfall_mm ?? "—"}
                    <small>mm</small>
                  </strong>
                  <span>Forecast rainfall</span>
                </div>
                <div>
                  <strong>
                    {w.temperature_c ?? "—"}
                    <small>°C</small>
                  </strong>
                  <span>Temperature</span>
                </div>
              </div>
              <p>{w.source}</p>
              <small>{date(w.created_at)}</small>
              {w.error && <p className="danger-text">{w.error}</p>}
            </div>
          ))}
          {!snapshots.length && (
            <Empty
              title="Weather has not been loaded"
              body="Use the refresh control to request current data."
            />
          )}
        </div>
      </section>
      {selected && (
        <RiskDetails risk={selected} onClose={() => setSelectedZoneId(null)} />
      )}
    </>
  );
}
function RiskDetails({
  risk,
  onClose,
}: {
  risk: RiskType;
  onClose: () => void;
}) {
  const history = useApi<RiskType[]>(`/risk/history?zone_id=${risk.zone_id}`);
  return (
    <Modal
      open
      onClose={onClose}
      title={risk.zone_name}
      description={`Risk assessment calculated ${date(risk.created_at)}`}
      wide
    >
      <div className="risk-detail-summary">
        <div>
          <strong>
            {risk.score == null ? "—" : Math.round(risk.score)}
            <small>/100</small>
          </strong>
          <Badge>{risk.level}</Badge>
          <p>Normalized risk estimate · radius {risk.radius_km} km</p>
        </div>
      </div>
      <div className="detail-grid">
        <section>
          <h3>Contributing factors</h3>
          <RiskFactors factors={risk.factors} />
        </section>
        <section>
          <h3>Input provenance & limitations</h3>
          <ProvenanceSummary provenance={risk.provenance} />
        </section>
      </div>
      <section className="detail-section">
        <h3>
          <History size={17} />
          Assessment history
        </h3>
        {history.isLoading ? (
          <Loading />
        ) : history.error ? (
          <ErrorState error={history.error} />
        ) : history.data?.length ? (
          <div className="history-list">
            {history.data.slice(0, 12).map((h) => (
              <div key={h.id}>
                <span>{date(h.created_at)}</span>
                <div className="score-track">
                  <i style={{ width: `${h.score || 0}%` }} />
                </div>
                <strong>{h.score ?? "—"}</strong>
                <Badge>{h.level}</Badge>
              </div>
            ))}
          </div>
        ) : (
          <Empty title="No prior assessments" />
        )}
      </section>
    </Modal>
  );
}
