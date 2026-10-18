import { useState } from "react";
import {
  Activity,
  Check,
  ChevronDown,
  ChevronUp,
  Network,
  RotateCcw,
  ShieldCheck,
  ScanLine,
  Waves,
  Waypoints,
  X,
} from "lucide-react";
import { api, date, json, useAction, useApi } from "../lib/api";
import type { Json } from "../lib/types";
import {
  Badge,
  Button,
  Empty,
  ErrorState,
  Field,
  JsonDetails,
  Loading,
  Modal,
} from "../components/UI";
export function Agents() {
  const executions = useApi<Json[]>("/agents"),
    recommendations = useApi<Json[]>("/recommendations");
  const [tab, setTab] = useState("recommendations"),
    [expanded, setExpanded] = useState<number | null>(null),
    [decision, setDecision] = useState<{ id: number; status: string } | null>(
      null,
    ),
    [reason, setReason] = useState("");
  const retry = useAction(
    (id: number) => api(`/agents/${id}/retry`, { method: "POST" }),
    "Agent execution retried",
  );
  const decide = useAction(async () => {
    await api(`/recommendations/${decision?.id}`, {
      method: "PATCH",
      body: json({ status: decision?.status, reason }),
    });
    setDecision(null);
    setReason("");
  }, "Recommendation reviewed");
  return (
    <>
      <div className="agent-intro">
        <Network size={28} />
        <div>
          <h2>Three agents. One coordinated picture.</h2>
          <p>
            Civic Intelligence analyzes hazards, Disaster Risk assesses
            conditions, and the Response Coordinator recommends human reviewed
            action.
          </p>
        </div>
      </div>
      <section className="panel agent-overview" aria-label="Specialist responsibilities">
        <div className="panel-heading">
          <div><h2>Specialist responsibilities</h2><p>Recorded analysis, transparent methods, human decisions</p></div>
          <Badge>Authority review required</Badge>
        </div>
        <div className="agent-grid">
          {[
            { name: "Civic Intelligence Agent", title: "Civic Intelligence", icon: ScanLine, method: "Report text rules · vision when configured", purpose: "Classifies the reported hazard, screens possible duplicates, and suggests a department." },
            { name: "Disaster Risk Agent", title: "Disaster Risk", icon: Waves, method: "Weighted engine · contextual interpretation", purpose: "Explains calculated zone estimates using weather, reported water hazards, and recorded history." },
            { name: "Response Coordinator Agent", title: "Response Coordinator", icon: Waypoints, method: "Rules and validated specialist handoffs", purpose: "Proposes response priorities and actions for an authority to approve, reject, or override." },
          ].map(({ name, title, icon: Icon, method, purpose }) => {
            const latest = executions.data?.filter((run) => run.agent === name).sort((a, b) => b.id - a.id)[0];
            const pending = recommendations.data?.filter((item) => item.agent === name && item.status === "Pending").length;
            const actualMethod = name === "Civic Intelligence Agent" && latest
              ? latest.output?.image_analyzed ? "Vision model + report context" : "Deterministic report text rules"
              : method;
            return <article className="agent-card" key={name}>
              <div className="agent-card-top section-line"><span className="agent-icon"><Icon size={19} /></span>{latest && <Badge>{latest.status}</Badge>}</div>
              <h3>{title}</h3><small className="agent-method">{actualMethod}</small>
              <p className="agent-summary">{purpose}</p>
              <p className="muted">{latest ? latest.summary : executions.isLoading ? "Loading recorded executions…" : executions.error ? "Execution history unavailable." : "No execution has been recorded yet."}</p>
              <footer className="agent-footer"><small>{latest ? `Last recorded ${date(latest.created_at)}` : "Awaiting a recorded run"}</small>
                <button className="text-link" onClick={() => { setTab("executions"); setExpanded(latest?.id ?? null); }}>{pending === undefined ? "Inspect activity" : `${pending} pending · Inspect activity`}</button>
              </footer>
            </article>;
          })}
        </div>
      </section>
      <div className="tabs" role="tablist">
        <button
          role="tab"
          aria-selected={tab === "recommendations"}
          className={tab === "recommendations" ? "active" : ""}
          onClick={() => setTab("recommendations")}
        >
          Recommendations{" "}
          <span>
            {recommendations.data?.filter((r) => r.status === "Pending")
              .length || 0}
          </span>
        </button>
        <button
          role="tab"
          aria-selected={tab === "executions"}
          className={tab === "executions" ? "active" : ""}
          onClick={() => setTab("executions")}
        >
          Execution log <span>{executions.data?.length || 0}</span>
        </button>
      </div>
      {tab === "recommendations" ? (
        recommendations.isLoading ? (
          <Loading />
        ) : recommendations.error ? (
          <ErrorState error={recommendations.error} />
        ) : (
          <div className="recommendations-list">
            {recommendations.data?.map((r) => (
              <section className="panel recommendation" key={r.id}>
                <div className="recommendation-icon">
                  <ShieldCheck size={25} />
                </div>
                <div className="recommendation-content">
                  <div className="section-line">
                    <span className="agent-name">
                      {r.agent}{" "}
                      {r.incident_id ? `· Incident #${r.incident_id}` : ""}
                    </span>
                    <div className="inline-badges">
                      <Badge>{r.priority}</Badge>
                      <Badge>{r.status}</Badge>
                    </div>
                  </div>
                  <h3>{r.action}</h3>
                  <p>{r.reason}</p>
                  <small>{date(r.created_at)}</small>
                  {r.review_reason && (
                    <p className="notice">Review: {r.review_reason}</p>
                  )}
                  <div className="inline-actions">
                    <Button
                      className="button-secondary small"
                      onClick={() => {
                        setDecision({ id: r.id, status: "Approved" });
                        setReason("");
                      }}
                    >
                      <Check size={14} />
                      Approve
                    </Button>
                    <Button
                      className="button-ghost small"
                      onClick={() => {
                        setDecision({ id: r.id, status: "Rejected" });
                        setReason("");
                      }}
                    >
                      <X size={14} />
                      Reject
                    </Button>
                    <Button
                      className="button-ghost small"
                      onClick={() => {
                        setDecision({ id: r.id, status: "Overridden" });
                        setReason("");
                      }}
                    >
                      Override decision
                    </Button>
                  </div>
                </div>
              </section>
            ))}
            {!recommendations.data?.length && (
              <Empty
                title="No recommendations yet"
                body="The agents will recommend actions after analyzing reports or refreshing risk."
              />
            )}
          </div>
        )
      ) : executions.isLoading ? (
        <Loading />
      ) : executions.error ? (
        <ErrorState error={executions.error} />
      ) : (
        <section className="panel executions">
          {executions.data?.map((a) => (
            <div className="execution" key={a.id}>
              <div className="execution-header">
                <span className="agent-symbol">
                  <Activity size={21} />
                </span>
                <div>
                  <strong>{a.agent}</strong>
                  <small>
                    {date(a.created_at)} · Attempt {a.attempts}{" "}
                    {a.incident_id ? `· Incident #${a.incident_id}` : ""}
                  </small>
                </div>
                <Badge>{a.status}</Badge>
                {a.status === "Failed" && (
                  <Button
                    className="button-ghost small"
                    pending={retry.isPending}
                    onClick={() => retry.mutate(a.id)}
                  >
                    <RotateCcw size={14} />
                    Retry
                  </Button>
                )}
                <button
                  className="icon-button"
                  aria-label={`Inspect execution ${a.id}`}
                  onClick={() => setExpanded(expanded === a.id ? null : a.id)}
                >
                  {expanded === a.id ? (
                    <ChevronUp size={18} />
                  ) : (
                    <ChevronDown size={18} />
                  )}
                </button>
              </div>
              <p>{a.summary}</p>
              {a.error && <p className="form-error">{a.error}</p>}
              {expanded === a.id && (
                <div className="detail-grid">
                  <section>
                    <h4>Input context</h4>
                    <JsonDetails data={a.input_context} />
                  </section>
                  <section>
                    <h4>Validated output</h4>
                    <JsonDetails data={a.output} />
                  </section>
                </div>
              )}
            </div>
          ))}
          {!executions.data?.length && <Empty title="No executions recorded" />}
        </section>
      )}
      {decision && (
        <Modal
          open
          title={`${decision.status === "Approved" ? "Approve" : decision.status === "Rejected" ? "Reject" : "Override"} recommendation`}
          description="Your decision is stored in the audit log. Recommendations never execute actions without human approval."
          onClose={() => setDecision(null)}
        >
          <form
            className="stack"
            onSubmit={(e) => {
              e.preventDefault();
              decide.mutate(undefined);
            }}
          >
            <Field label="Decision reason">
              <textarea
                required
                minLength={5}
                rows={4}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Explain your review decision"
              />
            </Field>
            <Button pending={decide.isPending}>Confirm decision</Button>
          </form>
        </Modal>
      )}
    </>
  );
}
