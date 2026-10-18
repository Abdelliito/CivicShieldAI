import { useState } from "react";
import {
  Archive,
  ArrowRight,
  CheckCircle2,
  ClipboardList,
  Edit3,
  Link2,
  MapPin,
  Play,
  RefreshCw,
  Send,
  Trash2,
  UploadCloud,
} from "lucide-react";
import { api, date, json, upload, useAction, useApi } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { Entity, Incident, Assignment } from "../lib/types";
import { CATEGORIES, SEVERITIES, STATUSES } from "../lib/types";
import {
  Badge,
  Button,
  Empty,
  ErrorState,
  Evidence,
  Field,
  JsonDetails,
  Loading,
  Modal,
} from "./UI";
import { ReportForm } from "./ReportForm";
import { CivicMap } from "./Map";
import { AnalysisSummary } from "./IntelligenceSummary";
export function IncidentDetails({
  id,
  onClose,
}: {
  id: number;
  onClose: () => void;
}) {
  const { user } = useAuth();
  const query = useApi<Incident>(`/incidents/${id}`);
  const incident = query.data;
  const operator = user?.role === "authority" || user?.role === "admin";
  const [tab, setTab] = useState("Overview"),
    [edit, setEdit] = useState(false),
    [classify, setClassify] = useState(false),
    [note, setNote] = useState(""),
    [noteEdit, setNoteEdit] = useState<number | null>(null),
    [team, setTeam] = useState(""),
    [assignmentNotes, setAssignmentNotes] = useState(""),
    [status, setStatus] = useState(""),
    [reason, setReason] = useState(""),
    [target, setTarget] = useState(""),
    [completion, setCompletion] = useState<File | null>(null),
    [completionNotes, setCompletionNotes] = useState(""),
    [additionalEvidence, setAdditionalEvidence] = useState<File | null>(null);
  const teams = useApi<Entity[]>("/teams", operator);
  const departments = useApi<Entity[]>("/departments", operator);
  const allIncidents = useApi<Incident[]>("/incidents", operator);
  const act = useAction(
    async ({
      path,
      method = "POST",
      body,
    }: {
      path: string;
      method?: string;
      body?: unknown;
    }) => api(path, { method, body: body ? json(body) : undefined }),
  );
  const saveNote = useAction(async () => {
    await api(noteEdit ? `/notes/${noteEdit}` : `/incidents/${id}/notes`, {
      method: noteEdit ? "PATCH" : "POST",
      body: json({ body: note }),
    });
    setNote("");
    setNoteEdit(null);
  }, "Note saved");
  const assign = useAction(async () => {
    await api(`/incidents/${id}/assignments`, {
      method: "POST",
      body: json({ team_id: Number(team), notes: assignmentNotes }),
    });
    setTeam("");
    setAssignmentNotes("");
  }, "Response team assigned");
  const submitCompletion = useAction(async (assignment: Assignment) => {
    if (!completion)
      throw new Error("Add completion evidence before submitting.");
    if (completionNotes.trim().length < 10)
      throw new Error("Describe the completed work in at least 10 characters.");
    await upload(completion, id, "completion");
    await api(`/assignments/${assignment.id}`, {
      method: "PATCH",
      body: json({ status: "Submitted", notes: completionNotes.trim() }),
    });
    setCompletion(null);
    setCompletionNotes("");
  }, "Completion submitted for authority verification");
  const addEvidence = useAction(async () => {
    if (!additionalEvidence) throw new Error("Choose a photograph first.");
    await upload(additionalEvidence, id, "report");
    setAdditionalEvidence(null);
  }, "Additional evidence uploaded");
  const current = incident?.assignments?.find(
    (a) => a.status !== "Cancelled" && a.status !== "Submitted",
  );
  return (
    <>
      <Modal
        open
        onClose={onClose}
        title={incident?.reference || "Incident details"}
        description="Incident record · every change is saved to the activity history."
        wide
      >
        {query.isLoading ? (
          <Loading />
        ) : query.error ? (
          <ErrorState error={query.error} retry={() => void query.refetch()} />
        ) : (
          incident && (
            <div className="incident-detail">
              <div className="detail-title">
                <div>
                  <div className="inline-badges">
                    <Badge>{incident.severity}</Badge>
                    <Badge>{incident.status}</Badge>
                    {incident.archived && <Badge>Archived</Badge>}
                  </div>
                  <h2>{incident.title}</h2>
                  <p>
                    <MapPin size={14} />
                    {incident.location_name}{" "}
                    <span>· Reported {date(incident.created_at)}</span>
                  </p>
                </div>
                {user?.role === "citizen" &&
                  !incident.duplicate_of &&
                  !incident.archived &&
                  [
                    "Submitted",
                    "Under Analysis",
                    "Pending Review",
                    "Rejected",
                    "Reopened",
                  ].includes(incident.status) && (
                    <Button
                      className="button-secondary"
                      onClick={() => setEdit(true)}
                    >
                      <Edit3 size={15} />
                      Edit report
                    </Button>
                  )}
              </div>
              <div className="tabs" role="tablist">
                {["Overview", "Response", "Evidence", "Activity"].map(
                  (item) => (
                    <button
                      type="button"
                      role="tab"
                      aria-selected={tab === item}
                      key={item}
                      className={tab === item ? "active" : ""}
                      onClick={() => setTab(item)}
                    >
                      {item}
                      {item === "Evidence" && incident.attachments?.length
                        ? ` (${incident.attachments.length})`
                        : ""}
                    </button>
                  ),
                )}
              </div>
              {tab === "Overview" && (
                <>
                  <div className="detail-grid">
                    <section>
                      <h3>Citizen report</h3>
                      <p className="description-text">{incident.description}</p>
                      <dl className="info-grid">
                        <div>
                          <dt>Classification</dt>
                          <dd>{incident.category}</dd>
                        </div>
                        <div>
                          <dt>Department</dt>
                          <dd>
                            {departments.data?.find(
                              (d) => d.id === incident.department_id,
                            )?.name ||
                              incident.analysis?.recommended_department ||
                              "Awaiting routing"}
                          </dd>
                        </div>
                        <div>
                          <dt>Coordinates</dt>
                          <dd>
                            {incident.latitude.toFixed(5)},{" "}
                            {incident.longitude.toFixed(5)}
                          </dd>
                        </div>
                        <div>
                          <dt>Last updated</dt>
                          <dd>{date(incident.updated_at)}</dd>
                        </div>
                      </dl>
                      {incident.duplicate_of && (
                        <p className="notice">
                          <Link2 size={16} />
                          Consolidated with incident{" "}
                          {incident.consolidated_incident?.reference ||
                            `incident #${incident.duplicate_of}`}{" "}
                          ·{" "}
                          {incident.consolidated_incident?.status ||
                            "Status available through authority review"}
                          . Original report preserved.
                        </p>
                      )}
                    </section>
                    <div className="map-frame">
                      <CivicMap height={230} incidents={[incident]} controls={false} />
                    </div>
                  </div>
                  <section className="detail-section">
                    <div className="section-line">
                      <h3>Civic Intelligence analysis</h3>
                      {operator && (
                        <div className="inline-actions">
                          <Button
                            className="button-ghost small"
                            onClick={() => setClassify(true)}
                          >
                            <Edit3 size={14} />
                            Review classification
                          </Button>
                          <Button
                            className="button-secondary small"
                            pending={act.isPending}
                            onClick={() =>
                              act.mutate({ path: `/incidents/${id}/analyze` })
                            }
                          >
                            <RefreshCw size={14} />
                            Re-analyze
                          </Button>
                        </div>
                      )}
                    </div>
                    <p className="notice">
                      {incident.analysis?.image_analyzed === true
                        ? "Model assisted analysis · human verification required."
                        : "Transparent deterministic analysis · image understanding requires a configured vision provider."}
                    </p>
                    <AnalysisSummary analysis={incident.analysis} />
                  </section>
                  {operator && (
                    <section className="detail-section">
                      <h3>Duplicate review</h3>
                      <p className="muted">
                        Compare related reports. Merging preserves original
                        reports and evidence.
                      </p>
                      {incident.duplicates &&
                        incident.duplicates.length > 0 && (
                          <JsonDetails data={incident.duplicates} />
                        )}
                      <div className="inline-controls">
                        <select
                          aria-label="Related incident"
                          value={target}
                          onChange={(e) => setTarget(e.target.value)}
                        >
                          <option value="">Choose a related incident</option>
                          {allIncidents.data
                            ?.filter((i) => i.id !== id)
                            .map((i) => (
                              <option key={i.id} value={i.id}>
                                {i.reference} · {i.title}
                              </option>
                            ))}
                        </select>
                        {["merge", "reject", "separate"].map((action) => (
                          <Button
                            key={action}
                            className="button-secondary small"
                            disabled={!target}
                            pending={act.isPending}
                            onClick={() => {
                              if (
                                confirm(
                                  `${action === "merge" ? "Merge this report with" : action === "reject" ? "Reject the duplicate relationship with" : "Separate this report from"} incident #${target}?`,
                                )
                              )
                                act.mutate({
                                  path: `/incidents/${id}/duplicate`,
                                  body: { target_id: Number(target), action },
                                });
                            }}
                          >
                            {action === "merge"
                              ? "Confirm merge"
                              : action === "reject"
                                ? "Reject match"
                                : "Separate"}
                          </Button>
                        ))}
                      </div>
                    </section>
                  )}
                </>
              )}
              {tab === "Response" && (
                <>
                  <div className="detail-grid">
                    <section>
                      <h3>Response assignment</h3>
                      {incident.assignments?.length ? (
                        incident.assignments.map((assignment) => (
                          <div className="assignment" key={assignment.id}>
                            <div className="section-line">
                              <strong>
                                {assignment.team_name ||
                                  teams.data?.find(
                                    (t) => t.id === assignment.team_id,
                                  )?.name ||
                                  `Team ${assignment.team_id}`}
                              </strong>
                              <Badge>{assignment.status}</Badge>
                            </div>
                            <p>{assignment.notes || "No assignment notes."}</p>
                            <small>{date(assignment.created_at)}</small>
                            {operator && assignment.status !== "Cancelled" && (
                              <div className="inline-actions">
                                <Button
                                  className="button-ghost danger-text small"
                                  onClick={() => {
                                    if (confirm("Cancel this assignment?"))
                                      act.mutate({
                                        path: `/assignments/${assignment.id}`,
                                        method: "PATCH",
                                        body: {
                                          status: "Cancelled",
                                          notes: "Cancelled by authority",
                                        },
                                      });
                                  }}
                                >
                                  Cancel assignment
                                </Button>
                              </div>
                            )}
                          </div>
                        ))
                      ) : (
                        <Empty
                          title="No team assigned"
                          body="An authority will review and route this incident."
                        />
                      )}
                      {operator && (
                        <form
                          className="stack"
                          onSubmit={(e) => {
                            e.preventDefault();
                            assign.mutate(undefined);
                          }}
                        >
                          <Field label="Assign / reassign team">
                            <select
                              required
                              value={team}
                              onChange={(e) => setTeam(e.target.value)}
                            >
                              <option value="">Select response team</option>
                              {teams.data
                                ?.filter((t) => t.active)
                                .map((t) => (
                                  <option key={t.id} value={t.id}>
                                    {t.name}
                                  </option>
                                ))}
                            </select>
                          </Field>
                          <Field label="Assignment instructions">
                            <textarea
                              value={assignmentNotes}
                              onChange={(e) =>
                                setAssignmentNotes(e.target.value)
                              }
                              rows={2}
                            />
                          </Field>
                          <Button pending={assign.isPending} disabled={!team}>
                            <ClipboardList size={15} />
                            Assign team
                          </Button>
                        </form>
                      )}
                    </section>
                    <section>
                      <h3>Status & verification</h3>
                      <p className="muted">Current incident status</p>
                      <Badge>{incident.status}</Badge>
                      {operator && (
                        <form
                          className="stack top-space"
                          onSubmit={(e) => {
                            e.preventDefault();
                            act.mutate({
                              path: `/incidents/${id}/status`,
                              body: { status, reason },
                            });
                          }}
                        >
                          <Field label="New status">
                            <select
                              required
                              value={status}
                              onChange={(e) => setStatus(e.target.value)}
                            >
                              <option value="">Choose a status</option>
                              {STATUSES.map((s) => (
                                <option key={s}>{s}</option>
                              ))}
                            </select>
                          </Field>
                          <Field label="Status update reason">
                            <textarea
                              required
                              minLength={3}
                              value={reason}
                              onChange={(e) => setReason(e.target.value)}
                              rows={3}
                              placeholder="Explain your decision or correction request"
                            />
                          </Field>
                          <Button disabled={!status} pending={act.isPending}>
                            <CheckCircle2 size={15} />
                            Update status
                          </Button>
                          <p className="muted">
                            Select Closed to verify a resolution, or In Progress
                            to request corrections.
                          </p>
                        </form>
                      )}
                      {user?.role === "worker" && current && (
                        <div className="stack top-space">
                          {current.status === "Assigned" && (
                            <Button
                              onClick={() =>
                                act.mutate({
                                  path: `/assignments/${current.id}`,
                                  method: "PATCH",
                                  body: { status: "Acknowledged" },
                                })
                              }
                            >
                              Accept assignment
                              <ArrowRight size={15} />
                            </Button>
                          )}
                          {current.status === "Acknowledged" && (
                            <Button
                              onClick={() =>
                                act.mutate({
                                  path: `/assignments/${current.id}`,
                                  method: "PATCH",
                                  body: { status: "In Progress" },
                                })
                              }
                            >
                              <Play size={15} />
                              Start work
                            </Button>
                          )}
                          {current.status === "In Progress" && (
                            <form
                              className="stack"
                              onSubmit={(e) => {
                                e.preventDefault();
                                submitCompletion.mutate(current);
                              }}
                            >
                              <Field label="Completion evidence">
                                <input
                                  required
                                  type="file"
                                  accept="image/*"
                                  onChange={(e) =>
                                    setCompletion(e.target.files?.[0] || null)
                                  }
                                />
                              </Field>
                              {completion && (
                                <p className="muted">{completion.name}</p>
                              )}
                              <Field label="Completion notes" hint="At least 10 characters describing the completed work.">
                                <textarea
                                  required
                                  minLength={10}
                                  rows={3}
                                  value={completionNotes}
                                  onChange={(e) =>
                                    setCompletionNotes(e.target.value)
                                  }
                                  placeholder="Describe the completed work and evidence"
                                />
                              </Field>
                              <Button pending={submitCompletion.isPending}>
                                <UploadCloud size={16} />
                                Submit completion
                              </Button>
                            </form>
                          )}
                        </div>
                      )}
                    </section>
                  </div>
                  <section className="detail-section">
                    <div className="section-line">
                      <h3>Updates & notes</h3>
                      {operator && !incident.archived && (
                        <Button
                          className="button-secondary small"
                          pending={act.isPending}
                          onClick={() =>
                            act.mutate({
                              path: `/incidents/${id}/notes`,
                              body: {
                                body: "Additional evidence requested: please upload a clear photograph of the hazard and its surroundings in the Evidence tab.",
                              },
                            })
                          }
                        >
                          Request additional evidence
                        </Button>
                      )}
                    </div>
                    {incident.notes?.length ? (
                      incident.notes.map((n) => (
                        <div className="note" key={n.id}>
                          <div className="section-line">
                            <strong>
                              {n.author_name ||
                                `User ${n.user_id || n.author_id}`}
                            </strong>
                            <small>{date(n.created_at)}</small>
                          </div>
                          <p>{n.body}</p>
                          {(user?.role === "admin" ||
                            n.user_id === user?.id ||
                            n.author_id === user?.id) && (
                            <div className="inline-actions">
                              <button
                                className="text-link"
                                onClick={() => {
                                  setNote(n.body);
                                  setNoteEdit(n.id);
                                }}
                              >
                                Edit
                              </button>
                              <button
                                className="text-link danger-text"
                                onClick={() => {
                                  if (confirm("Delete this note?"))
                                    act.mutate({
                                      path: `/notes/${n.id}`,
                                      method: "DELETE",
                                    });
                                }}
                              >
                                Delete
                              </button>
                            </div>
                          )}
                        </div>
                      ))
                    ) : (
                      <p className="muted">No updates yet.</p>
                    )}
                    {!incident.archived && (
                      <form
                        className="inline-controls"
                        onSubmit={(e) => {
                          e.preventDefault();
                          saveNote.mutate(undefined);
                        }}
                      >
                        <input
                          aria-label="Incident note"
                          required
                          minLength={2}
                          placeholder={
                            noteEdit
                              ? "Edit your note"
                              : "Add an update for this incident…"
                          }
                          value={note}
                          onChange={(e) => setNote(e.target.value)}
                        />
                        <Button pending={saveNote.isPending}>
                          <Send size={15} />
                          {noteEdit ? "Save note" : "Add note"}
                        </Button>
                        {noteEdit && (
                          <Button
                            type="button"
                            className="button-ghost"
                            onClick={() => {
                              setNoteEdit(null);
                              setNote("");
                            }}
                          >
                            Cancel
                          </Button>
                        )}
                      </form>
                    )}
                  </section>
                </>
              )}
              {tab === "Evidence" && (
                <>
                  <p className="muted">
                    Original report images and completion evidence are preserved
                    with the incident.
                  </p>
                  {(operator || user?.role === "citizen") &&
                    !incident.archived &&
                    !["Closed", "Resolved", "Rejected", "Withdrawn"].includes(
                      incident.status,
                    ) && (
                      <form
                        className="evidence-upload-form inline-controls"
                        onSubmit={(e) => {
                          e.preventDefault();
                          addEvidence.mutate(undefined);
                        }}
                      >
                        <Field label="Additional photograph">
                          <input
                            type="file"
                            required
                            accept="image/jpeg,image/png,image/webp"
                            onChange={(e) =>
                              setAdditionalEvidence(e.target.files?.[0] || null)
                            }
                          />
                        </Field>
                        <Button
                          pending={addEvidence.isPending}
                          disabled={!additionalEvidence}
                        >
                          <UploadCloud size={15} />
                          Upload evidence
                        </Button>
                      </form>
                    )}
                  <div className="evidence-grid">
                    {incident.attachments?.map((a) => (
                      <Evidence
                        key={a.id}
                        attachment={a}
                        onDelete={
                          user?.role === "admin" &&
                          !incident.archived &&
                          !["Closed", "Resolved"].includes(incident.status)
                            ? () => {
                                if (
                                  confirm(
                                    "Remove this evidence? The audit record is preserved.",
                                  )
                                )
                                  act.mutate({
                                    path: `/uploads/${a.id}`,
                                    method: "DELETE",
                                  });
                              }
                            : undefined
                        }
                      />
                    ))}
                    {!incident.attachments?.length && (
                      <Empty
                        title="No photographs yet"
                        body="Evidence will appear when it is uploaded."
                      />
                    )}
                  </div>
                </>
              )}
              {tab === "Activity" && (
                <div className="timeline">
                  {incident.history?.length ? (
                    incident.history.map((event, index) => (
                      <div className="timeline-event" key={event.id || index}>
                        <i />
                        <div>
                          <strong>
                            {event.action ||
                              event.event ||
                              event.status ||
                              "Record updated"}
                          </strong>
                          <p>
                            {event.description ||
                              event.reason ||
                              event.detail ||
                              event.details ||
                              event.body ||
                              ""}
                          </p>
                          <small>
                            {date(event.created_at)} ·{" "}
                            {event.actor_name ||
                              event.user_name ||
                              `User ${event.user_id || event.actor_id || "system"}`}
                          </small>
                        </div>
                      </div>
                    ))
                  ) : (
                    <Empty title="No activity recorded" />
                  )}
                </div>
              )}
              <div className="detail-bottom">
                <span className="muted">
                  {incident.reference} · Persistent civic incident record
                </span>
                {user?.role === "citizen" &&
                  (incident.status === "Withdrawn" ||
                    (!incident.duplicate_of &&
                      !incident.archived &&
                      [
                        "Submitted",
                        "Under Analysis",
                        "Pending Review",
                        "Rejected",
                        "Reopened",
                      ].includes(incident.status))) && (
                    <Button
                      className="button-ghost danger-text small"
                      pending={act.isPending}
                      onClick={() => {
                        if (
                          confirm(
                            incident.status === "Withdrawn"
                              ? "Restore this report for review?"
                              : "Withdraw this report? You can restore it later.",
                          )
                        )
                          act.mutate({
                            path: `/reports/${id}/withdraw`,
                            body: { restore: incident.status === "Withdrawn" },
                          });
                      }}
                    >
                      {incident.status === "Withdrawn" ? (
                        <RefreshCw size={14} />
                      ) : (
                        <Trash2 size={14} />
                      )}{" "}
                      {incident.status === "Withdrawn"
                        ? "Restore report"
                        : "Withdraw report"}
                    </Button>
                  )}
                {operator && (
                  <Button
                    className="button-ghost small"
                    pending={act.isPending}
                    onClick={() => {
                      if (
                        confirm(
                          incident.archived
                            ? "Restore this incident from the archive?"
                            : "Archive this incident? Its records will be preserved.",
                        )
                      )
                        act.mutate({
                          path: `/incidents/${id}/archive`,
                          body: { archived: !incident.archived },
                        });
                    }}
                  >
                    <Archive size={15} />
                    {incident.archived
                      ? "Restore incident"
                      : "Archive incident"}
                  </Button>
                )}
              </div>
            </div>
          )
        )}
      </Modal>
      {edit && incident && (
        <ReportForm open onClose={() => setEdit(false)} incident={incident} />
      )}
      {classify && incident && (
        <Classification
          incident={incident}
          departments={departments.data || []}
          onClose={() => setClassify(false)}
        />
      )}
    </>
  );
}
function Classification({
  incident,
  departments,
  onClose,
}: {
  incident: Incident;
  departments: Entity[];
  onClose: () => void;
}) {
  const [category, setCategory] = useState(incident.category),
    [severity, setSeverity] = useState(incident.severity),
    [department, setDepartment] = useState(
      String(incident.department_id || ""),
    ),
    [reason, setReason] = useState("");
  const action = useAction(async () => {
    await api(`/incidents/${incident.id}`, {
      method: "PATCH",
      body: json({
        category,
        severity,
        department_id: department ? Number(department) : null,
        reason,
      }),
    });
    onClose();
  }, "Classification updated");
  return (
    <Modal
      open
      onClose={onClose}
      title="Review classification"
      description="Human decisions override automated recommendations and remain in the audit history."
    >
      <form
        className="stack"
        onSubmit={(e) => {
          e.preventDefault();
          action.mutate(undefined);
        }}
      >
        <Field label="Hazard category">
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            {[...new Set([incident.category, ...CATEGORIES])].map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </Field>
        <Field label="Severity">
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
          >
            {SEVERITIES.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </Field>
        <Field label="Department">
          <select
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
          >
            <option value="">Unassigned</option>
            {departments
              .filter((d) => d.active)
              .map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
          </select>
        </Field>
        <Field label="Justification">
          <textarea
            required
            minLength={5}
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Explain why this classification is appropriate"
          />
        </Field>
        <Button pending={action.isPending}>Save classification</Button>
      </form>
    </Modal>
  );
}
