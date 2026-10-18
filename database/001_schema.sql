-- CivicShield AI PostgreSQL schema; generated from backend/app/models.py.

-- Run against a fresh PostgreSQL database. No credentials are embedded.

BEGIN;

CREATE TABLE departments (
	id SERIAL NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	description TEXT NOT NULL, 
	active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE zones (
	id SERIAL NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	latitude FLOAT NOT NULL, 
	longitude FLOAT NOT NULL, 
	radius_km FLOAT NOT NULL, 
	historical_floods INTEGER NOT NULL, 
	active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT valid_zone_measurements CHECK (radius_km > 0 AND historical_floods >= 0), 
	UNIQUE (name)
);

CREATE TABLE risk_assessments (
	id SERIAL NOT NULL, 
	zone_id INTEGER NOT NULL, 
	score FLOAT, 
	level VARCHAR(30) NOT NULL, 
	factors JSON NOT NULL, 
	provenance JSON NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(zone_id) REFERENCES zones (id)
);

CREATE INDEX ix_risk_assessments_zone_id ON risk_assessments (zone_id);

CREATE TABLE teams (
	id SERIAL NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	department_id INTEGER NOT NULL, 
	active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name), 
	FOREIGN KEY(department_id) REFERENCES departments (id)
);

CREATE TABLE weather_snapshots (
	id SERIAL NOT NULL, 
	zone_id INTEGER, 
	rainfall_mm FLOAT, 
	forecast_rainfall_mm FLOAT, 
	temperature_c FLOAT, 
	source VARCHAR(180) NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	data JSON NOT NULL, 
	error TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(zone_id) REFERENCES zones (id)
);

CREATE TABLE users (
	id SERIAL NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	email VARCHAR(254) NOT NULL, 
	password_hash TEXT NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	team_id INTEGER, 
	active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT valid_user_role CHECK (role IN ('citizen','authority','worker','admin')), 
	FOREIGN KEY(team_id) REFERENCES teams (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE incidents (
	id SERIAL NOT NULL, 
	reference VARCHAR(40) NOT NULL, 
	title VARCHAR(180) NOT NULL, 
	description TEXT NOT NULL, 
	category VARCHAR(80) NOT NULL, 
	severity VARCHAR(20) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	latitude FLOAT NOT NULL, 
	longitude FLOAT NOT NULL, 
	location_name VARCHAR(240) NOT NULL, 
	zone_id INTEGER, 
	department_id INTEGER, 
	team_id INTEGER, 
	citizen_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	archived BOOLEAN NOT NULL, 
	analysis JSON NOT NULL, 
	duplicate_of INTEGER, 
	PRIMARY KEY (id), 
	CONSTRAINT valid_incident_severity CHECK (severity IN ('Low','Medium','High','Critical')), 
	CONSTRAINT valid_incident_status CHECK (status IN ('Submitted','Under Analysis','Pending Review','Assigned','In Progress','Resolved','Closed','Rejected','Withdrawn','Reopened')), 
	CONSTRAINT valid_incident_location CHECK (latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180), 
	UNIQUE (reference), 
	FOREIGN KEY(zone_id) REFERENCES zones (id), 
	FOREIGN KEY(department_id) REFERENCES departments (id), 
	FOREIGN KEY(team_id) REFERENCES teams (id), 
	FOREIGN KEY(citizen_id) REFERENCES users (id), 
	FOREIGN KEY(duplicate_of) REFERENCES incidents (id)
);

CREATE INDEX ix_incidents_status ON incidents (status);

CREATE INDEX ix_incidents_citizen_id ON incidents (citizen_id);

CREATE TABLE agent_executions (
	id SERIAL NOT NULL, 
	agent VARCHAR(80) NOT NULL, 
	incident_id INTEGER, 
	status VARCHAR(30) NOT NULL, 
	summary TEXT NOT NULL, 
	input_context JSON NOT NULL, 
	output JSON NOT NULL, 
	error TEXT, 
	attempts INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(incident_id) REFERENCES incidents (id)
);

CREATE INDEX ix_agent_executions_incident_id ON agent_executions (incident_id);

CREATE TABLE assignments (
	id SERIAL NOT NULL, 
	incident_id INTEGER NOT NULL, 
	team_id INTEGER NOT NULL, 
	assigned_by INTEGER NOT NULL, 
	worker_id INTEGER,
	sharing_scope VARCHAR(20) DEFAULT 'full_report' NOT NULL,
	status VARCHAR(30) NOT NULL, 
	notes TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT valid_assignment_status CHECK (status IN ('Assigned','Acknowledged','In Progress','Submitted','Cancelled')), 
	CONSTRAINT valid_assignment_sharing_scope CHECK (sharing_scope IN ('full_report','location_only')),
	FOREIGN KEY(incident_id) REFERENCES incidents (id), 
	FOREIGN KEY(team_id) REFERENCES teams (id), 
	FOREIGN KEY(assigned_by) REFERENCES users (id),
	FOREIGN KEY(worker_id) REFERENCES users (id)
);

CREATE INDEX ix_assignments_incident_id ON assignments (incident_id);

CREATE TABLE attachments (
	id SERIAL NOT NULL, 
	incident_id INTEGER, 
	user_id INTEGER NOT NULL, 
	filename VARCHAR(255) NOT NULL, 
	storage_name VARCHAR(80) NOT NULL, 
	content_type VARCHAR(60) NOT NULL, 
	kind VARCHAR(30) NOT NULL, 
	deleted BOOLEAN NOT NULL, 
	analysis JSON DEFAULT '{}' NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(incident_id) REFERENCES incidents (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	UNIQUE (storage_name)
);

CREATE INDEX ix_attachments_incident_id ON attachments (incident_id);

CREATE TABLE audit_logs (
	id SERIAL NOT NULL, 
	incident_id INTEGER, 
	user_id INTEGER, 
	action VARCHAR(100) NOT NULL, 
	detail TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(incident_id) REFERENCES incidents (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_audit_logs_incident_id ON audit_logs (incident_id);

CREATE TABLE duplicate_candidates (
	id SERIAL NOT NULL, 
	incident_id INTEGER NOT NULL, 
	target_id INTEGER NOT NULL, 
	score FLOAT NOT NULL, 
	distance_m FLOAT NOT NULL, 
	similarity FLOAT NOT NULL, 
	reason TEXT NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT unique_duplicate_pair UNIQUE (incident_id, target_id), 
	FOREIGN KEY(incident_id) REFERENCES incidents (id), 
	FOREIGN KEY(target_id) REFERENCES incidents (id)
);

CREATE TABLE notes (
	id SERIAL NOT NULL, 
	incident_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	body TEXT NOT NULL, 
	deleted BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(incident_id) REFERENCES incidents (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_notes_incident_id ON notes (incident_id);

CREATE TABLE notifications (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	incident_id INTEGER, 
	title VARCHAR(180) NOT NULL, 
	body TEXT NOT NULL, 
	read BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(incident_id) REFERENCES incidents (id)
);

CREATE INDEX ix_notifications_user_id ON notifications (user_id);

CREATE TABLE recommendations (
	id SERIAL NOT NULL, 
	incident_id INTEGER, 
	agent VARCHAR(80) NOT NULL, 
	action TEXT NOT NULL, 
	reason TEXT NOT NULL, 
	priority VARCHAR(30) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(incident_id) REFERENCES incidents (id)
);

CREATE INDEX ix_recommendations_incident_id ON recommendations (incident_id);

CREATE TABLE reports (
	id SERIAL NOT NULL, 
	incident_id INTEGER NOT NULL, 
	citizen_id INTEGER NOT NULL, 
	original_description TEXT NOT NULL, 
	withdrawn BOOLEAN NOT NULL, 
	previous_status VARCHAR(30), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (incident_id), 
	FOREIGN KEY(incident_id) REFERENCES incidents (id), 
	FOREIGN KEY(citizen_id) REFERENCES users (id)
);

COMMIT;
