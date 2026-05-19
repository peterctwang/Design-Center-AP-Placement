"""Application configuration via .env / env vars."""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AI Wall Design"
    debug: bool = True

    # Storage paths (relative to backend/)
    base_dir: Path = Path(__file__).resolve().parent.parent
    data_dir: Path = base_dir / "data"
    upload_dir: Path = base_dir / "data" / "uploads"
    report_dir: Path = base_dir / "data" / "reports"
    heatmap_dir: Path = base_dir / "data" / "heatmaps"
    static_dir: Path = base_dir / "static"

    # DB
    database_url: str = f"sqlite:///{base_dir / 'data' / 'app.db'}"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8000"]

    class Config:
        env_file = ".env"


settings = Settings()

# Ensure directories exist on import
for d in (settings.data_dir, settings.upload_dir, settings.report_dir,
          settings.heatmap_dir, settings.static_dir):
    d.mkdir(parents=True, exist_ok=True)
