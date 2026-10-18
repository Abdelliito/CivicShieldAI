"""Idempotent repair for early local demo seeds. No operational records deleted."""
from sqlalchemy import select
from .config import settings
from .db import SessionLocal
from .models import Department, Incident, Team


def main():
    if not settings.demo_mode:
        raise RuntimeError('This repair only runs in explicit DEMO_MODE.')
    with SessionLocal() as db:
        old = db.scalar(select(Department).where(Department.name == 'Electrical Services'))
        new = db.scalar(select(Department).where(Department.name == 'Electricity & Streetlights'))
        if old and not new:
            old.name = 'Electricity & Streetlights'
        general = db.scalar(select(Department).where(Department.name == 'General Civic Services'))
        if not general:
            general = Department(name='General Civic Services', description='Human triage for uncertain or other civic hazards.')
            db.add(general)
            db.flush()
            db.add(Team(name='General Civic Review Team', department_id=general.id))
        departments = db.scalars(select(Department)).all()
        for incident in db.scalars(select(Incident).where(Incident.department_id.is_(None))):
            suggested = incident.analysis.get('recommended_department', '')
            department = next((d for d in departments if d.name == suggested), None)
            if department:
                incident.department_id = department.id
        db.commit()
    print('Local synthetic seed names and missing routing suggestions repaired; operational history retained.')


if __name__ == '__main__':
    main()
