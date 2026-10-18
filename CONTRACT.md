# Shared implementation contract

All API routes prefixed `/api`. JSON keys snake_case. Auth Bearer JWT, `/auth/login` JSON `{email,password}` => `{access_token,user}`; `/auth/me`; `/auth/register` citizen only. Demo password `CivicDemo!2026`, emails `citizen@civicshield.demo`, `authority@civicshield.demo`, `worker@civicshield.demo`, `admin@civicshield.demo`. Explicit DEMO_MODE seeding only.

Entities use integer `id`. Reports linked to one incident, incident fields: id, reference, title, description, category, severity (Low/Medium/High/Critical), status (Submitted/Under Analysis/Pending Review/Assigned/In Progress/Resolved/Closed/Rejected/Withdrawn/Reopened), latitude, longitude, location_name, zone_id, department_id, team_id, citizen_id, created_at, updated_at, archived, analysis JSON, duplicate_of optional. Seed synthetic Lahore data clearly labeled.

GET `/incidents` => JSON array, search/category/status/severity/zone_id/from_date/to_date/include_archived filters. Citizens see own; workers assigned team only. POST `/reports` => incident with title,description,latitude,longitude,location_name,attachment_ids optional. GET `/incidents/{id}` => fields + notes, attachments, history, assignments, duplicates, recommendations. PATCH `/reports/{id}` citizen edit; POST `/reports/{id}/withdraw` `{restore?:boolean}`. PATCH `/incidents/{id}` authority edit with reason required on severity override. POST `/incidents/{id}/status` `{status,reason}`. POST `/incidents/{id}/archive` `{archived:boolean}`. POST `/incidents/{id}/analyze`. POST `/incidents/{id}/duplicate` `{target_id,action:merge|reject|separate}`.

Timezone-free and date-only incident filter values use UTC. Explicit timestamp offsets are preserved. A midnight `to_date` includes that whole calendar day in its supplied timezone; other end timestamps are inclusive. These bounds do not inherit the PostgreSQL session timezone.

POST `/uploads` multipart file => `{id,url,filename}` optional incident_id and kind (report/completion). Authenticated GET `/uploads/{id}/file` or token-bearing fetch via client blob. DELETE `/uploads/{id}`. GET attachment lists in details.

POST `/incidents/{id}/notes` `{body}`; PATCH `/notes/{id}` `{body}`; DELETE `/notes/{id}`.

POST `/incidents/{id}/assignments` `{team_id,notes}`; PATCH `/assignments/{id}` `{team_id?,status?,notes?}` statuses Assigned/Acknowledged/In Progress/Submitted/Cancelled. Worker completion requires completion attachment and notes, then sets incident Resolved awaiting authority Closed. Authority can cancel/reassign, verify Closed or corrections In Progress.

GET/POST `/departments`, `/teams`, `/zones`, `/users`; PATCH/DELETE `/{entity}/{id}`. DELETE soft deactivates, PATCH active true reactivates. Admin mutations; authority can read departments/teams/zones, admin users only. Department {name,description,active}; team {name,department_id,active}; zone {name,latitude,longitude,radius_km,historical_floods,active}; user {name,email,role,team_id,password?,active}.

GET `/notifications`; PATCH `/notifications/{id}` `{read:boolean}`. GET `/dashboard` => {total,new,unresolved,critical,awaiting_review,active,resolved,recent_activity}; GET `/audit` array. GET `/health`.

GET `/risk` latest assessments array; POST `/risk/refresh` `{scenario?:"heavy_rain"|"clear"|"missing"}` => array; GET `/risk/history?zone_id=`; GET `/weather` stored weather. GET `/agents` execution array; GET `/recommendations` array; PATCH `/recommendations/{id}` `{status:Approved|Rejected|Overridden,reason?}`; POST `/agents/{id}/retry`.

Risk assessment: {id,zone_id,zone_name,score,level:Low|Moderate|High|Insufficient Data,factors:JSON,provenance:JSON,created_at,latitude,longitude,radius_km}. Agent execution {id,agent,incident_id,status,summary,input_context,output,created_at,error,attempts}. Recommendation {id,incident_id,agent,action,reason,priority,status,created_at}.

Backend Python SQLAlchemy sync, PostgreSQL via psycopg2, FastAPI. Backend agent owns models/db/core APIs; intelligence agent owns `backend/app/intelligence.py` + unit tests, exporting `analyze_incident(db, incident)`, `refresh_risk(db, scenario=None, fetch_live=True)`, `run_pipeline(db,incident)`, `refresh_weather(db)`; coordinate model names directly. Frontend React TypeScript Vite, Leaflet, no mocked operational data; all mutations go to APIs. API error `{detail:string}`. Frontend proxy /api and /uploads to 127.0.0.1:8000. Frontend port 5173. Database URL configured in .env at project root.
