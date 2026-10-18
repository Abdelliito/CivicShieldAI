import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / '.env')


class Settings:
    database_url = os.getenv('DATABASE_URL', 'postgresql+psycopg2://civicshield:civicshield@127.0.0.1:5432/civicshield')
    jwt_secret = os.getenv('JWT_SECRET', '')
    demo_mode = os.getenv('DEMO_MODE', 'false').lower() == 'true'
    openai_api_key = os.getenv('OPENAI_API_KEY', '')
    openai_model = os.getenv('OPENAI_MODEL', 'gpt-4.1-mini')
    upload_dir = Path(os.getenv('UPLOAD_DIR', str(ROOT / 'backend' / 'uploads')))
    cors_origins = [v.strip() for v in os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',')]
    weather_refresh_minutes = int(os.getenv('WEATHER_REFRESH_MINUTES', '30'))


settings = Settings()
