import { useState } from "react";
import { Bell, Check, Circle } from "lucide-react";
import { api, date, json, useAction, useApi } from "../lib/api";
import type { Json } from "../lib/types";
import { Button, Empty, ErrorState, Loading } from "../components/UI";
export function Notifications({ onOpen }: { onOpen: (id: number) => void }) {
  const [unread, setUnread] = useState(false);
  const query = useApi<Json[]>("/notifications");
  const mark = useAction(
    ({ id, read }: { id: number; read: boolean }) =>
      api(`/notifications/${id}`, { method: "PATCH", body: json({ read }) }),
    "Notification updated",
  );
  const items = (query.data || []).filter((n) => !unread || !n.read);
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>Your notifications</h2>
          <p>Updates on reports, assignments, and authority decisions</p>
        </div>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={unread}
            onChange={(e) => setUnread(e.target.checked)}
          />
          Unread only
        </label>
      </div>
      {query.isLoading ? (
        <Loading />
      ) : query.error ? (
        <ErrorState error={query.error} retry={() => void query.refetch()} />
      ) : items.length ? (
        <div className="notifications-list">
          {items.map((n) => (
            <div
              className={`notification ${n.read ? "" : "unread"}`}
              key={n.id}
            >
              <span className="notification-icon">
                <Bell size={20} />
              </span>
              <div>
                <strong>{n.title}</strong>
                <p>{n.body}</p>
                <small>{date(n.created_at)}</small>
                {n.incident_id && (
                  <button
                    className="text-link"
                    onClick={() => onOpen(n.incident_id)}
                  >
                    View incident
                  </button>
                )}
              </div>
              <Button
                className="button-ghost small"
                pending={mark.isPending}
                onClick={() => mark.mutate({ id: n.id, read: !n.read })}
              >
                {n.read ? <Circle size={13} /> : <Check size={14} />}Mark{" "}
                {n.read ? "unread" : "read"}
              </Button>
            </div>
          ))}
        </div>
      ) : (
        <Empty
          title={unread ? "You’re all caught up" : "No notifications yet"}
          body="Report and response updates will appear here."
        />
      )}
    </section>
  );
}
