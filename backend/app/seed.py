"""Opt-in, synthetic Lahore demonstration data. Never auto-enabled in production."""
from datetime import timedelta
from PIL import Image, ImageDraw
from sqlalchemy import select
from .config import settings
from .models import *
from .security import hash_password
from .services import choose_zone

DEMO_PASSWORD = 'CivicDemo!2026'


def ensure_demo_media():
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    for number in (7, 8):
        path = settings.upload_dir / f'demo-completion-{number}.jpg'
        if path.is_file():
            continue
        image = Image.new('RGB', (1000, 650), '#e4f1ec')
        drawing = ImageDraw.Draw(image)
        drawing.rectangle((80, 180, 920, 480), fill='#647675')
        drawing.rectangle((440, 190, 560, 470), fill='#283e3c')
        for y in range(210, 460, 30):
            drawing.line((450, y, 550, y), fill='#bccbc6', width=8)
        drawing.text((60, 55), 'SYNTHETIC COMPLETION EVIDENCE', fill='#163e35', font_size=32)
        drawing.text((60, 540), 'Illustration for demo workflow only - not a real photograph.', fill='#163e35', font_size=22)
        image.save(path, 'JPEG')


def seed_demo(db):
    if not settings.demo_mode:
        raise RuntimeError('Demo seeding is disabled. Set DEMO_MODE=true only for local demonstrations.')
    ensure_demo_media()
    if db.scalar(select(User).where(User.email == 'admin@civicshield.demo')):
        return
    departments = [
        Department(name='Water & Sanitation', description='Synthetic municipal drainage, sewer and water operations.'),
        Department(name='Roads & Infrastructure', description='Road surfaces, manholes and civil infrastructure.'),
        Department(name='Electricity & Streetlights', description='Electrical cables, wiring and street lighting.'),
        Department(name='Solid Waste Management', description='Garbage collection and public-space sanitation.'),
        Department(name='Traffic Engineering', description='Traffic signals and road-safety equipment.'),
        Department(name='General Civic Services', description='Human triage for uncertain or other civic hazards.'),
    ]
    db.add_all(departments)
    db.flush()
    teams = [Team(name=name, department_id=dep.id) for name, dep in zip(['Drainage Response · Central', 'Road Maintenance · East', 'Electrical Safety · Lahore', 'Sanitation Field Unit', 'Traffic Signals Unit', 'General Civic Review Team'], departments)]
    db.add_all(teams)
    db.flush()
    users = [User(name=name, email=f'{role}@civicshield.demo', role=role, password_hash=hash_password(DEMO_PASSWORD), team_id=teams[0].id if role == 'worker' else None) for role, name in [('citizen', 'Ayesha Khan'), ('authority', 'Omar Farooq'), ('worker', 'Ali Hassan'), ('admin', 'System Administrator')]]
    db.add_all(users)
    db.flush()
    citizen, authority, worker, administrator = users
    zones = [
        Zone(name='Gulberg', latitude=31.5114, longitude=74.3506, radius_km=2.3, historical_floods=7),
        Zone(name='Jail Road', latitude=31.5350, longitude=74.3310, radius_km=1.5, historical_floods=5),
        Zone(name='Model Town', latitude=31.4815, longitude=74.3239, radius_km=2.2, historical_floods=2),
        Zone(name='Johar Town', latitude=31.4697, longitude=74.2728, radius_km=2.5, historical_floods=4),
    ]
    db.add_all(zones)
    db.flush()
    for zone in zones:
        db.add(WeatherSnapshot(zone_id=zone.id, rainfall_mm=18.0, forecast_rainfall_mm=42.0 if zone.id == zones[0].id else 23.0, temperature_c=27.0, source='Synthetic Lahore demonstration scenario', is_demo=True, data={'label': 'Synthetic example; not an observed forecast', 'historical_data': 'Synthetic flood counts for demonstration'}))
    examples = [
        ('Blocked drain near Liberty Market', 'Drain blocked by leaves and plastic. Water is pooling across the pedestrian crossing near Liberty Market after rain.', 31.5146, 74.3494, 'Liberty Market, Gulberg', 'Pending Review', 0),
        ('Water rising at Main Boulevard', 'Standing water has accumulated across the main road near a blocked drainage inlet. Several cars and pedestrians pass here.', 31.5098, 74.3521, 'Main Boulevard, Gulberg', 'In Progress', 0),
        ('Open manhole beside school entrance', 'An open manhole without a cover is next to the school entrance. Children walk past it and the hole is deep.', 31.5348, 74.3308, 'Jail Road, Lahore', 'Pending Review', 1),
        ('Exposed electrical cable on footpath', 'A fallen live high voltage electrical cable is exposed on a wet footpath. There are sparks and pedestrians nearby.', 31.5118, 74.3468, 'MM Alam Road, Gulberg', 'Pending Review', 2),
        ('Overflowing sewer near community park', 'Sewer overflow is spilling wastewater into the street and blocking access to the community park after rain.', 31.4804, 74.3233, 'Model Town Link Road', 'Assigned', 0),
        ('Large pothole at intersection', 'A large pothole and broken road surface at the busy intersection are causing motorcyclists to swerve into traffic.', 31.4702, 74.2718, 'G1 Market, Johar Town', 'Pending Review', 1),
        ('Streetlight repaired near bus stop', 'The damaged streetlight beside the bus stop is not illuminating the pavement at night and needs repair.', 31.5334, 74.3286, 'Jail Road Bus Stop', 'Closed', 2),
        ('Drainage clearing awaiting verification', 'The storm drain is blocked with garbage and water has accumulated outside several shops after rainfall.', 31.5130, 74.3528, 'Hussain Chowk, Gulberg', 'Resolved', 0),
        ('Garbage blocking neighborhood access', 'Garbage accumulation has covered the footpath outside the housing block, attracting insects and restricting access.', 31.4685, 74.2742, 'Johar Town Block G', 'Pending Review', 3),
        ('Leaking water main beside road', 'A broken water main is leaking continuously onto the road and eroding the shoulder next to the footpath.', 31.4823, 74.3250, 'Model Town C Block', 'Assigned', 0),
        ('Second report of Liberty drain blockage', 'Drain blocked by leaves and plastic. Water is pooling across the pedestrian crossing near Liberty Market after rain.', 31.5147, 74.3495, 'Liberty Market, Gulberg', 'Pending Review', 0),
        ('Traffic signal showing no lights', 'The traffic signal is damaged and all lights are out at the intersection. Vehicles are crossing without guidance.', 31.4708, 74.2746, 'Johar Town Main Boulevard', 'Pending Review', 4),
    ]
    from .intelligence import run_pipeline, refresh_risk
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    for index, (title, description, lat, lon, location, status, department_index) in enumerate(examples):
        incident = Incident(reference=f'CS-DEMO-{index+1:04d}', title=title, description=description + ' [Synthetic demonstration report.]', latitude=lat, longitude=lon, location_name=location, citizen_id=citizen.id, zone_id=choose_zone(db, lat, lon), status='Pending Review', created_at=utcnow() - timedelta(hours=2 + index * 3))
        db.add(incident)
        db.flush()
        db.add(Report(incident_id=incident.id, citizen_id=citizen.id, original_description=incident.description))
        run_pipeline(db, incident)
        incident.status = status
        incident.department_id = departments[department_index].id
        if status in {'Assigned', 'In Progress', 'Resolved', 'Closed'}:
            incident.team_id = teams[department_index].id
            assignment = Assignment(incident_id=incident.id, team_id=teams[department_index].id, assigned_by=authority.id, status='Submitted' if status in {'Resolved', 'Closed'} else status, notes='Synthetic demo: preventive maintenance completed; please inspect before verification.' if status in {'Resolved', 'Closed'} else 'Synthetic demo assignment: inspect location and address the reported hazard.')
            db.add(assignment)
        db.add(AuditLog(incident_id=incident.id, user_id=authority.id, action=f'Synthetic demo record: {status}', detail='Seeded for the hackathon demonstration; not a real municipal incident.'))
        db.add(Note(incident_id=incident.id, user_id=authority.id, body='Synthetic demonstration record. This is a simulated municipal operations environment.'))
        if status in {'Resolved', 'Closed'}:
            storage = f'demo-completion-{index+1}.jpg'
            db.add(Attachment(incident_id=incident.id, user_id=worker.id, filename='synthetic-completion-evidence.jpg', storage_name=storage, content_type='image/jpeg', kind='completion'))
    db.add(Notification(user_id=citizen.id, title='Welcome to CivicShield AI', body='Your reports and scenario weather are synthetic. Submit a new report to test the real persisted workflow.'))
    refresh_risk(db, fetch_live=False)
    db.commit()


if __name__ == '__main__':
    from .db import Base, SessionLocal, engine
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        seed_demo(session)
