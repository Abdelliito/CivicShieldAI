import { ChevronRight } from "lucide-react";
import type { Incident } from "../lib/types";
import { date, relative } from "../lib/api";
import { Badge, Empty } from "./UI";
export function IncidentTable({
  incidents,
  onOpen,
  compact = false,
}: {
  incidents: Incident[];
  onOpen: (id: number) => void;
  compact?: boolean;
}) {
  return incidents.length ? (
    <div className="table-scroll">
      <table className={`data-table ${compact ? "compact" : ""}`}>
        <thead>
          <tr>
            <th>Reference</th>
            <th>Incident</th>
            {!compact && <th>Category</th>}
            <th>Severity</th>
            <th>Status</th>
            <th>Reported</th>
            <th>
              <span className="sr-only">Details</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {incidents.map((i) => (
            <tr key={i.id} onClick={() => onOpen(i.id)}>
              <td>
                <button
                  className="reference-link"
                  onClick={(e) => {
                    e.stopPropagation();
                    onOpen(i.id);
                  }}
                >
                  {i.reference}
                </button>
                {i.archived && <small className="block muted">Archived</small>}
              </td>
              <td>
                <strong>{i.title}</strong>
                {!compact && (
                  <small className="block muted">{i.location_name}</small>
                )}
              </td>
              {!compact && <td>{i.category}</td>}
              <td>
                <Badge>{i.severity}</Badge>
              </td>
              <td>
                <Badge>{i.status}</Badge>
              </td>
              <td className="muted nowrap"><time dateTime={i.created_at} title={date(i.created_at)}>{relative(i.created_at)}</time></td>
              <td>
                <button
                  aria-label={`View ${i.reference}`}
                  className="icon-button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onOpen(i.id);
                  }}
                >
                  <ChevronRight size={17} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : (
    <Empty
      title="No incidents found"
      body="Try changing your filters, or submit a new civic report."
    />
  );
}
