import type { Json } from "../lib/types";
import { Badge, JsonDetails } from "./UI";
import { date } from "../lib/api";
export function AnalysisSummary({ analysis }: { analysis: Json }) {
  return (
    <div className="analysis-summary">
      <p>
        {analysis.summary ||
          "No completed analysis is recorded for this report."}
      </p>
      <dl className="info-grid">
        <div>
          <dt>Suggested classification</dt>
          <dd>{analysis.category || "Unclassified"}</dd>
        </div>
        <div>
          <dt>Suggested department</dt>
          <dd>{analysis.recommended_department || "Human routing required"}</dd>
        </div>
        <div>
          <dt>Analysis method</dt>
          <dd>
            {analysis.image_analyzed
              ? "Vision model + report context"
              : "Deterministic report text rules"}
          </dd>
        </div>
        <div>
          <dt>Image analysis</dt>
          <dd>
            {analysis.image_analyzed
              ? "Photograph processed by the configured vision model"
              : "Photograph retained as evidence; not analyzed"}
          </dd>
        </div>
      </dl>
      {analysis.evidence?.length > 0 && (
        <ul className="evidence-facts">
          {analysis.evidence.map((e: string, i: number) => (
            <li key={i}>{e}</li>
          ))}
        </ul>
      )}
      {analysis.uncertainty?.length > 0 && (
        <p className="analysis-uncertainty">{analysis.uncertainty.join(" ")}</p>
      )}
      <JsonDetails data={analysis} />
    </div>
  );
}
export function RiskFactors({ factors }: { factors: Json }) {
  const labels: Record<string, string> = {
    forecast_rain_mm: "Forecast rainfall",
    recent_rain_mm: "Recent rainfall",
    unresolved_blocked_drains: "Unresolved blocked drains",
    unresolved_water_incidents: "Water related hazards",
    historical_floods: "Historical flood events",
  };
  return (
    <div className="analysis-summary">
      <p>
        {factors.explanation ||
          "Inspect the underlying factors for this estimate."}
      </p>
      <dl className="factor-list">
        {Object.entries(factors.inputs || {}).map(([key, value]) => (
          <div key={key}>
            <dt>{labels[key] || key.replaceAll("_", " ")}</dt>
            <dd>
              {value == null ? "Unavailable" : String(value)}
              {key.endsWith("_mm") && value != null ? " mm" : ""}
            </dd>
          </div>
        ))}
      </dl>
      {factors.missing?.length > 0 && (
        <p className="analysis-uncertainty">
          Missing information: {factors.missing.join(", ")}.
        </p>
      )}
      {factors.limitations?.length > 0 && (
        <p className="analysis-uncertainty">{factors.limitations.join(" ")}</p>
      )}
      <JsonDetails data={factors} />
    </div>
  );
}
export function ProvenanceSummary({ provenance }: { provenance: Json }) {
  const weather = provenance.weather || {};
  return (
    <div className="analysis-summary">
      <dl className="factor-list">
        <div>
          <dt>Risk engine</dt>
          <dd>{provenance.model || "Weighted risk engine"}</dd>
        </div>
        <div>
          <dt>Weather source</dt>
          <dd>{weather.source || "See recorded source"}</dd>
        </div>
        <div>
          <dt>Weather captured</dt>
          <dd>{date(weather.created_at || weather.captured_at)}</dd>
        </div>
        <div>
          <dt>Historical inputs</dt>
          <dd>{provenance.history?.source || "Source recorded below"}</dd>
        </div>
        <div>
          <dt>Calculation trigger</dt>
          <dd>
            {String(provenance.trigger || "Stored assessment").replaceAll(
              "_",
              " ",
            )}
          </dd>
        </div>
      </dl>
      {(weather.is_demo || provenance.history?.synthetic) && (
        <Badge>Synthetic inputs included</Badge>
      )}
      <JsonDetails data={provenance} />
    </div>
  );
}
