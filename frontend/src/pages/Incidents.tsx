import { useState } from "react";
import { Filter, Search, X } from "lucide-react";
import { useApi } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { Entity, Incident } from "../lib/types";
import { CATEGORIES, SEVERITIES, STATUSES, statusLabel } from "../lib/types";
import { Empty, ErrorState, Loading } from "../components/UI";
import { IncidentTable } from "../components/IncidentTable";
export function Incidents({ onOpen }: { onOpen: (id: number) => void }) {
  const { user } = useAuth();
  const [search, setSearch] = useState(""),
    [status, setStatus] = useState(""),
    [category, setCategory] = useState(""),
    [severity, setSeverity] = useState(""),
    [zone, setZone] = useState(""),
    [from, setFrom] = useState(""),
    [to, setTo] = useState(""),
    [archived, setArchived] = useState(false),
    [page, setPage] = useState(0);
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  if (status) params.set("status", status);
  if (category) params.set("category", category);
  if (severity) params.set("severity", severity);
  if (zone) params.set("zone_id", zone);
  if (from) params.set("from_date", new Date(from + "T00:00:00").toISOString());
  if (to) params.set("to_date", new Date(to + "T23:59:59.999").toISOString());
  if (archived) params.set("include_archived", "true");
  const incidents = useApi<Incident[]>(`/incidents?${params}`);
  const zones = useApi<Entity[]>(
    "/zones",
    user?.role === "admin" || user?.role === "authority",
  );
  const data = incidents.data || [];
  const filters = !!(
    search ||
    status ||
    category ||
    severity ||
    zone ||
    from ||
    to ||
    archived
  );
  function clear() {
    setSearch("");
    setStatus("");
    setCategory("");
    setSeverity("");
    setZone("");
    setFrom("");
    setTo("");
    setArchived(false);
    setPage(0);
  }
  return (
    <section className="panel incidents-panel">
      <div className="filters">
        <div className="search-input">
          <Search size={17} />
          <input
            aria-label="Search incidents"
            placeholder="Search incidents, references, locations…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(0);
            }}
          />
        </div>
        <div className="filter-row">
          <Filter size={15} />
          <select
            aria-label="Status filter"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(0);
            }}
          >
            <option value="">All statuses</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>{statusLabel(s)}</option>
            ))}
          </select>
          <select
            aria-label="Severity filter"
            value={severity}
            onChange={(e) => {
              setSeverity(e.target.value);
              setPage(0);
            }}
          >
            <option value="">All severities</option>
            {SEVERITIES.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
          <select
            aria-label="Category filter"
            value={category}
            onChange={(e) => {
              setCategory(e.target.value);
              setPage(0);
            }}
          >
            <option value="">All categories</option>
            {[...new Set([...CATEGORIES, ...data.map((i) => i.category)])].map(
              (s) => (
                <option key={s}>{s}</option>
              ),
            )}
          </select>
          {zones.data && (
            <select
              aria-label="Zone filter"
              value={zone}
              onChange={(e) => {
                setZone(e.target.value);
                setPage(0);
              }}
            >
              <option value="">All zones</option>
              {zones.data.map((z) => (
                <option key={z.id} value={z.id}>
                  {z.name}
                </option>
              ))}
            </select>
          )}
        </div>
        <div className="filter-row date-filters">
          <label>
            From{" "}
            <input
              type="date"
              aria-label="Reported from date"
              value={from}
              onChange={(e) => setFrom(e.target.value)}
            />
          </label>
          <label>
            To{" "}
            <input
              type="date"
              aria-label="Reported to date"
              value={to}
              onChange={(e) => setTo(e.target.value)}
            />
          </label>
          {(user?.role === "admin" || user?.role === "authority") && (
            <label className="checkbox">
              <input
                type="checkbox"
                checked={archived}
                onChange={(e) => setArchived(e.target.checked)}
              />
              Include archived
            </label>
          )}
          {filters && (
            <button className="text-link" onClick={clear}>
              <X size={13} />
              Clear filters
            </button>
          )}
          <span className="filter-count">
            {data.length} incident{data.length === 1 ? "" : "s"}
          </span>
        </div>
      </div>
      {incidents.isLoading ? (
        <Loading />
      ) : incidents.error ? (
        <ErrorState
          error={incidents.error}
          retry={() => void incidents.refetch()}
        />
      ) : data.length ? (
        <>
          <IncidentTable
            incidents={data.slice(page * 15, (page + 1) * 15)}
            onOpen={onOpen}
          />
          <div className="pagination">
            <span>
              Showing {Math.min(page * 15 + 1, data.length)}–
              {Math.min((page + 1) * 15, data.length)} of {data.length}
            </span>
            <button
              className="button button-secondary small"
              disabled={!page}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </button>
            <button
              className="button button-secondary small"
              disabled={(page + 1) * 15 >= data.length}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        </>
      ) : (
        <Empty
          title={
            user?.role === "worker"
              ? "No assigned incidents"
              : "No incidents match your filters"
          }
          body={
            user?.role === "worker"
              ? "Your assigned team work will appear here."
              : "Clear filters to see more reports, or create a new one."
          }
        />
      )}
    </section>
  );
}
