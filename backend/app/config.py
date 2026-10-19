import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
# PowerShell's UTF-8 files can include a BOM. Shell/container variables retain
# precedence; editing the project-root file takes effect on backend restart.
load_dotenv(ROOT / '.env', encoding='utf-8-sig', override=False)


class Settings:
    database_url = os.getenv('DATABASE_URL', 'postgresql+psycopg2://civicshield:civicshield@127.0.0.1:5432/civicshield')
    jwt_secret = os.getenv('JWT_SECRET', '')
    demo_mode = os.getenv('DEMO_MODE', 'false').lower() == 'true'
    gemini_api_key = os.getenv('GEMINI_API_KEY', os.getenv('GOOGLE_API_KEY', ''))
    gemini_model = os.getenv('GEMINI_MODEL', 'gemini-3.8-flash')
    vision_provider = os.getenv('VISION_PROVIDER', 'gemini')
    upload_dir = Path(os.getenv('UPLOAD_DIR', str(ROOT / 'backend' / 'uploads')))
    cors_origins = [v.strip() for v in os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',')]
    weather_refresh_minutes = int(os.getenv('WEATHER_REFRESH_MINUTES', '30'))


settings = Settings()
