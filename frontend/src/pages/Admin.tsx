import { useState } from "react";
import {
  Building2,
  Edit3,
  MapPinned,
  Plus,
  Search,
  ShieldCheck,
  Users,
} from "lucide-react";
import { api, date, json, useAction, useApi } from "../lib/api";
import type { Entity, Json } from "../lib/types";
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
const resources = [
  {
    key: "departments",
    label: "Departments",
    singular: "department",
    icon: Building2,
  },
  { key: "teams", label: "Teams", singular: "team", icon: Users },
  { key: "zones", label: "Zones", singular: "zone", icon: MapPinned },
  { key: "users", label: "Users", singular: "user", icon: ShieldCheck },
];
export function Admin() {
  const [tab, setTab] = useState("departments"),
    [editing, setEditing] = useState<Entity | true | null>(null),
    [search, setSearch] = useState("");
  const resource = resources.find((r) => r.key === tab);
  const query = useApi<Entity[]>(`/${tab}`);
  const departments = useApi<Entity[]>("/departments"),
    teams = useApi<Entity[]>("/teams");
  const active = useAction(
    ({ id, value }: { id: number; value: boolean }) =>
      api(`/${tab}/${id}`, {
        method: value ? "PATCH" : "DELETE",
        body: value ? json({ active: true }) : undefined,
      }),
    "Record availability updated",
  );
  const items = (query.data || []).filter((i) =>
    String(`${i.name} ${i.email || ""}`)
      .toLowerCase()
      .includes(search.toLowerCase()),
  );
  return (
    <>
      <div className="admin-tabs">
        {resources.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            className={tab === key ? "active" : ""}
            onClick={() => {
              setTab(key);
              setSearch("");
            }}
          >
            <Icon size={18} />
            {label}
          </button>
        ))}
        <button
          className={tab === "audit" ? "active" : ""}
          onClick={() => {
            setTab("audit");
            setSearch("");
          }}
        >
          Audit history
        </button>
      </div>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>{resource?.label || "Audit history"}</h2>
            <p>
              {tab === "audit"
                ? "Persistent administrative and operational activity"
                : "Manage the people and resources behind your response"}
            </p>
          </div>
          {resource && (
            <Button onClick={() => setEditing(true)}>
              <Plus size={16} />
              New {resource.singular}
            </Button>
          )}
        </div>
        {resource && (
          <div className="admin-search search-input">
            <Search size={17} />
            <input
              aria-label={`Search ${resource.label.toLowerCase()}`}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={`Search ${resource.label.toLowerCase()}…`}
            />
          </div>
        )}
        {query.isLoading ? (
          <Loading />
        ) : query.error ? (
          <ErrorState error={query.error} retry={() => void query.refetch()} />
        ) : items.length ? (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  {tab === "audit" ? (
                    <>
                      <th>Time</th>
                      <th>Action</th>
                      <th>Details</th>
                      <th>Actor</th>
                    </>
                  ) : (
                    <>
                      <th>Name</th>
                      <th>
                        {tab === "departments"
                          ? "Description"
                          : tab === "teams"
                            ? "Department"
                            : tab === "zones"
                              ? "Coordinates & radius"
                              : "Role & email"}
                      </th>
                      <th>
                        {tab === "zones"
                          ? "Historical events"
                          : tab === "users"
                            ? "Team"
                            : "ID"}
                      </th>
                      <th>Availability</th>
                      <th>Actions</th>
                    </>
                  )}
                </tr>
              </thead>
              <tbody>
                {items.map((item) =>
                  tab === "audit" ? (
                    <tr key={item.id}>
                      <td className="nowrap">{date(item.created_at)}</td>
                      <td>{item.action}</td>
                      <td>
                        {typeof item.detail === "object" ? (
                          <JsonDetails data={item.detail} />
                        ) : (
                          item.detail
                        )}
                      </td>
                      <td>#{item.user_id || "system"}</td>
                    </tr>
                  ) : (
                    <tr key={item.id}>
                      <td>
                        <strong>{item.name}</strong>
                      </td>
                      <td>
                        {tab === "departments" ? (
                          item.description || "—"
                        ) : tab === "teams" ? (
                          departments.data?.find(
                            (d) => d.id === item.department_id,
                          )?.name || `#${item.department_id}`
                        ) : tab === "zones" ? (
                          `${item.latitude.toFixed(4)}, ${item.longitude.toFixed(4)} · ${item.radius_km} km`
                        ) : (
                          <>
                            <span className="capitalize">{item.role}</span>
                            <small className="block muted">{item.email}</small>
                          </>
                        )}
                      </td>
                      <td>
                        {tab === "zones"
                          ? item.historical_floods
                          : tab === "users"
                            ? teams.data?.find((t) => t.id === item.team_id)
                                ?.name || "—"
                            : `#${item.id}`}
                      </td>
                      <td>
                        <Badge>{item.active ? "Active" : "Inactive"}</Badge>
                      </td>
                      <td>
                        <div className="inline-actions">
                          <Button
                            className="button-ghost small"
                            onClick={() => setEditing(item)}
                          >
                            <Edit3 size={14} />
                            Edit
                          </Button>
                          <Button
                            className={`button-ghost small ${item.active ? "danger-text" : ""}`}
                            pending={active.isPending}
                            onClick={() => {
                              if (
                                confirm(
                                  `${item.active ? "Deactivate" : "Reactivate"} ${item.name}? ${item.active ? "Existing records will be preserved." : ""}`,
                                )
                              )
                                active.mutate({
                                  id: item.id,
                                  value: !item.active,
                                });
                            }}
                          >
                            {item.active ? "Deactivate" : "Reactivate"}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty title="No records found" />
        )}
      </section>
      {editing && resource && (
        <EntityForm
          key={`${tab}-${editing === true ? "new" : editing.id}`}
          resource={tab}
          singular={resource.singular}
          entity={editing === true ? undefined : editing}
          departments={departments.data || []}
          teams={teams.data || []}
          onClose={() => setEditing(null)}
        />
      )}
    </>
  );
}
function EntityForm({
  resource,
  singular,
  entity,
  departments,
  teams,
  onClose,
}: {
  resource: string;
  singular: string;
  entity?: Entity;
  departments: Entity[];
  teams: Entity[];
  onClose: () => void;
}) {
  const [values, setValues] = useState<Json>({
    name: entity?.name || "",
    description: entity?.description || "",
    department_id: entity?.department_id || "",
    latitude: entity?.latitude ?? 31.5204,
    longitude: entity?.longitude ?? 74.3587,
    radius_km: entity?.radius_km ?? 2,
    historical_floods: entity?.historical_floods ?? 0,
    email: entity?.email || "",
    role: entity?.role || "citizen",
    team_id: entity?.team_id || "",
    password: "",
  });
  function set(key: string, value: any) {
    setValues((v) => ({ ...v, [key]: value }));
  }
  const save = useAction(
    async () => {
      const fields =
        resource === "departments"
          ? ["name", "description"]
          : resource === "teams"
            ? ["name", "department_id"]
            : resource === "zones"
              ? [
                  "name",
                  "latitude",
                  "longitude",
                  "radius_km",
                  "historical_floods",
                ]
              : ["name", "email", "role", "team_id", "password"];
      const payload: Json = {};
      fields.forEach((key) => {
        if (key === "password" && !values[key]) return;
        payload[key] = [
          "department_id",
          "latitude",
          "longitude",
          "radius_km",
          "historical_floods",
        ].includes(key)
          ? Number(values[key])
          : key === "team_id"
            ? values[key]
              ? Number(values[key])
              : null
            : values[key];
      });
      await api(`/${resource}${entity ? `/${entity.id}` : ""}`, {
        method: entity ? "PATCH" : "POST",
        body: json(payload),
      });
      onClose();
    },
    `${singular[0].toUpperCase() + singular.slice(1)} saved`,
  );
  return (
    <Modal
      open
      onClose={onClose}
      title={`${entity ? "Edit" : "New"} ${singular}`}
      description="Changes are persisted to the database and recorded in audit history."
    >
      <form
        className="stack"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate(undefined);
        }}
      >
        <Field label="Name">
          <input
            required
            minLength={2}
            maxLength={120}
            value={values.name}
            onChange={(e) => set("name", e.target.value)}
          />
        </Field>
        {resource === "departments" && (
          <Field label="Description">
            <textarea
              rows={3}
              value={values.description}
              onChange={(e) => set("description", e.target.value)}
            />
          </Field>
        )}
        {resource === "teams" && (
          <Field label="Department">
            <select
              required
              value={values.department_id}
              onChange={(e) => set("department_id", e.target.value)}
            >
              <option value="">Choose a department</option>
              {departments
                .filter((d) => d.active)
                .map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
            </select>
          </Field>
        )}
        {resource === "zones" && (
          <>
            <div className="form-grid">
              <Field label="Latitude">
                <input
                  required
                  type="number"
                  step="any"
                  min={-90}
                  max={90}
                  value={values.latitude}
                  onChange={(e) => set("latitude", e.target.value)}
                />
              </Field>
              <Field label="Longitude">
                <input
                  required
                  type="number"
                  step="any"
                  min={-180}
                  max={180}
                  value={values.longitude}
                  onChange={(e) => set("longitude", e.target.value)}
                />
              </Field>
            </div>
            <Field label="Radius (km)">
              <input
                required
                type="number"
                min={0.1}
                max={50}
                step={0.1}
                value={values.radius_km}
                onChange={(e) => set("radius_km", e.target.value)}
              />
            </Field>
            <Field
              label="Historical flood events"
              hint="Demonstration zones use synthetic historical observations."
            >
              <input
                required
                type="number"
                min={0}
                max={10000}
                value={values.historical_floods}
                onChange={(e) => set("historical_floods", e.target.value)}
              />
            </Field>
          </>
        )}
        {resource === "users" && (
          <>
            <Field label="Email address">
              <input
                required
                type="email"
                value={values.email}
                onChange={(e) => set("email", e.target.value)}
              />
            </Field>
            <Field label="Role">
              <select
                value={values.role}
                onChange={(e) => set("role", e.target.value)}
              >
                {["citizen", "authority", "worker", "admin"].map((r) => (
                  <option key={r}>{r}</option>
                ))}
              </select>
            </Field>
            <Field label="Team">
              <select
                value={values.team_id}
                onChange={(e) => set("team_id", e.target.value)}
              >
                <option value="">No assigned team</option>
                {teams
                  .filter((t) => t.active)
                  .map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
              </select>
            </Field>
            <Field label={entity ? "New password (optional)" : "Password"}>
              <input
                required={!entity}
                type="password"
                minLength={10}
                value={values.password}
                autoComplete="new-password"
                onChange={(e) => set("password", e.target.value)}
              />
            </Field>
          </>
        )}
        <div className="form-footer">
          <Button className="button-secondary" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button pending={save.isPending}>Save {singular}</Button>
        </div>
      </form>
    </Modal>
  );
}
