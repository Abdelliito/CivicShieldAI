import { Link } from "react-router-dom";
import { Activity, ArrowRight, Clock3, FileText, MapPin, Network } from "lucide-react";
import { useApi, relative, date } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { Incident, Json, Risk } from "../lib/types";
import { Badge, Empty, ErrorState, Loading } from "../components/UI";
import { CivicMap } from "../components/Map";
import { IncidentTable } from "../components/IncidentTable";

const AGENTS = [
  { name: "Civic Intelligence Agent", icon: FileText, method: "Hazard analysis" },
  { name: "Disaster Risk Agent", icon: Activity, method: "Weighted risk engine" },
  { name: "Response Coordinator Agent", icon: Network, method: "Rule-based planning" },
];

export function Dashboard({ onOpen }: { onOpen: (id: number) => void }) {
  const { user } = useAuth();
  const operator = user?.role === "authority" || user?.role === "admin";
  const incidents = useApi<Incident[]>("/incidents");
  const dashboard = useApi<Json>("/dashboard");
  const risks = useApi<Risk[]>("/risk", operator);
  const agents = useApi<Json[]>("/agents", operator);
  const recommendations = useApi<Json[]>("/recommendations", operator);

  if (incidents.isLoading || dashboard.isLoading) return <Loading />;
  if (incidents.error || dashboard.error) {
    return <ErrorState error={incidents.error || dashboard.error} retry={() => {
      void incidents.refetch(); void dashboard.refetch();
    }} />;
  }

  const data = incidents.data || [];
  const stats = dashboard.data || {};
  const priority = [...data]
    .filter((incident) => !["Closed", "Resolved", "Withdrawn", "Rejected"].includes(incident.status))
    .sort((a, b) => ["Critical", "High", "Medium", "Low"].indexOf(a.severity) - ["Critical", "High", "Medium", "Low"].indexOf(b.severity))
    .slice(0, 3);
  const metrics = [
    { label: operator ? "Total incidents" : "Your reports", value: stats.total ?? data.length, tone: "neutral", detail: `${stats.new ?? 0} new incidents` },
    { label: "Awaiting review", value: stats.awaiting_review ?? 0, tone: "warning", detail: `${stats.unresolved ?? 0} unresolved incidents` },
    { label: "Active assignments", value: stats.active ?? 0, tone: "positive", detail: `${stats.critical ?? 0} high / critical hazards` },
    { label: "Resolved", value: stats.resolved ?? 0, tone: "positive", detail: "Resolution progress" },
  ];

  return <div className={`atlas-overview ${operator ? "" : "personal-overview"}`}>
    <section className="operational-summary" aria-label="Operational summary">
      {metrics.map((metric) => <div className={`summary-item summary-${metric.tone}`} key={metric.label}>
        <h2>{metric.label}</h2>
        <div className="summary-value"><strong>{metric.value}</strong><span>{metric.detail}</span></div>
      </div>)}
    </section>

    <div className="dashboard-primary">
      <section className="panel operational-map">
        <div className="panel-heading">
          <div><h2>Operational map</h2><p>{data.length} records · Lahore · {operator ? "Local hazards & flood risk" : "Your reported hazards"}</p></div>
          <Link className="map-heading-link" to={operator ? "/risk" : "/incidents"}>Explore map <ArrowRight size={14} /></Link>
        </div>
        <CivicMap incidents={data} risks={risks.data || []} height={350} onIncident={onOpen} />
        {risks.isError && <div className="map-data-warning">Risk data is unavailable. Reported hazards remain visible.</div>}
      </section>

      <section className="panel priority-panel">
        <div className="panel-heading"><h2>{user?.role === "worker" ? "Assigned work" : "Priority queue"}</h2><Link to="/incidents">View all</Link></div>
        <div className="priority-list">
          {priority.length ? priority.map((incident, index) => <article className={`priority-item priority-${incident.severity.toLowerCase()}`} key={incident.id}>
            <span className="priority-rank">{index + 1}</span>
            <div className="priority-content">
              <div className="priority-meta"><Badge>{incident.severity}</Badge><span className="reference">{incident.reference}</span></div>
              <button className="priority-title" onClick={() => onOpen(incident.id)}>{incident.title}</button>
              <p className="priority-location"><MapPin size={13} />{incident.location_name}</p>
              <div className="priority-footer"><span><Clock3 size={12} />{relative(incident.created_at)}<b>·</b>{incident.status}</span><button className="text-link" onClick={() => onOpen(incident.id)}>{operator ? "Review incident" : user?.role === "worker" ? "Open task" : "View report"}<ArrowRight size={14} /></button></div>
            </div>
          </article>) : <Empty title="All clear in your queue" body="New unresolved incidents will appear here." />}
        </div>
      </section>
    </div>

    {operator ? <section className="panel operational-intelligence">
      <div className="panel-heading"><h2>Operational intelligence</h2><Link to="/agents">View all agents <ArrowRight size={14} /></Link></div>
      {agents.isError ? <ErrorState error={agents.error} retry={() => void agents.refetch()} /> : <div className="intelligence-columns">
        {AGENTS.map(({ name, icon: Icon, method }, index) => {
          const execution = agents.data?.find((entry) => entry.agent === name);
          const pending = recommendations.data?.filter((entry) => entry.agent === name && entry.status === "Pending").length || 0;
          const latestDecision = recommendations.data?.find((entry) => entry.agent === name);
          const actualMethod = name === "Civic Intelligence Agent"
            ? execution?.output?.image_analyzed ? "Vision model + report context" : "Deterministic report text rules"
            : method;
          const compactMethod = name === "Civic Intelligence Agent"
            ? execution?.output?.image_analyzed ? "Vision model" : "Text rules"
            : method;
          return <article className="intelligence-column" key={name}>
            <span className="intelligence-number">0{index + 1}</span>
            <div className="intelligence-content"><h3><Icon size={18} />{name}</h3>
              <p>{execution?.summary || (agents.isLoading ? "Loading the latest observation…" : "No execution has been recorded yet.")}</p>
              <div className="intelligence-meta"><span title={actualMethod}>{compactMethod}</span>{execution && <Badge>{execution.status}</Badge>}</div>
              <div className="intelligence-action">{execution && <time className="intelligence-time" dateTime={execution.created_at}>{date(execution.created_at)}</time>}{recommendations.isError ? <span>Recommendations unavailable</span> : recommendations.isLoading ? <span>Loading recommendation state…</span> : pending ? <Link to="/agents">{pending} awaiting review <ArrowRight size={12} /></Link> : <span>{latestDecision ? `Human decision: ${latestDecision.status}` : "No pending recommendation"}</span>}</div>
            </div>
          </article>;
        })}
      </div>}
    </section> : <section className="panel personal-journey"><div className="panel-heading"><h2>{user?.role === "worker" ? "From assignment to resolution" : "Your report makes a difference"}</h2><span className="muted">Every step is recorded</span></div><div className="journey">{["Report submitted", "Hazard analysis & review", "Team assigned", "Work completed", "Resolution verified"].map((label, index) => <div key={label}><span>{index + 1}</span><p>{label}</p></div>)}</div></section>}

    <section className="panel recent-panel">
      <div className="panel-heading"><h2>Recent incidents</h2><Link to="/incidents">View all</Link></div>
      <IncidentTable incidents={data.slice(0, 5)} onOpen={onOpen} compact />
    </section>
  </div>;
}
