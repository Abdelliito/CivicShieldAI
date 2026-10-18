export type Role = "citizen" | "authority" | "worker" | "admin";
export type Json = Record<string, any>;
export interface User {
  id: number;
  name: string;
  email: string;
  role: Role;
  team_id?: number | null;
  active: boolean;
}
export interface Attachment {
  id: number;
  filename: string;
  url?: string;
  kind?: string;
  content_type?: string;
  user_id?: number;
}
export interface Assignment {
  id: number;
  team_id: number;
  team_name?: string;
  status: string;
  notes?: string;
  created_at?: string;
  worker_id?: number | null;
  worker_name?: string | null;
  sharing_scope?: "full_report" | "location_only";
}
export interface Incident {
  id: number;
  reference: string;
  title: string;
  description: string;
  category: string;
  severity: string;
  status: string;
  latitude: number;
  longitude: number;
  location_name: string;
  zone_id?: number;
  department_id?: number;
  team_id?: number;
  citizen_id: number;
  created_at: string;
  updated_at: string;
  archived: boolean;
  analysis: Json;
  duplicate_of?: number | null;
  consolidated_incident?: { reference: string; status: string };
  attachments?: Attachment[];
  notes?: Json[];
  history?: Json[];
  assignments?: Assignment[];
  duplicates?: Json[];
  recommendations?: Json[];
  sharing_scope?: "full_report" | "location_only";
  sharing_notice?: string;
}
export interface Risk {
  id: number;
  zone_id: number;
  zone_name: string;
  score: number | null;
  level: string;
  factors: Json;
  provenance: Json;
  created_at: string;
  latitude: number;
  longitude: number;
  radius_km: number;
}
export interface Entity extends Json {
  id: number;
  name: string;
  active: boolean;
}
export const STATUSES = [
  "Submitted",
  "Under Analysis",
  "Pending Review",
  "Assigned",
  "In Progress",
  "Resolved",
  "Closed",
  "Rejected",
  "Withdrawn",
  "Reopened",
];
export const CATEGORIES = [
  "Potholes",
  "Broken roads",
  "Open manholes",
  "Blocked drainage",
  "Sewer overflow",
  "Water accumulation",
  "Garbage accumulation",
  "Water leakage",
  "Exposed electrical wiring",
  "Fallen electric cables",
  "Damaged streetlights",
  "Damaged traffic signals",
  "Other civic infrastructure hazards",
];
export const SEVERITIES = ["Low", "Medium", "High", "Critical"];
export const STATUS_LABELS: Record<string, string> = {
  Submitted: "Report received", "Under Analysis": "Checking report", "Pending Review": "Awaiting review",
  Assigned: "Team assigned", "In Progress": "Work in progress", Resolved: "Awaiting repair verification",
  Closed: "Closed · repair verified", Rejected: "Not accepted", Withdrawn: "Withdrawn", Reopened: "Needs further work",
};
export function statusLabel(status: string) { return STATUS_LABELS[status] || status; }
