import os
from typing import Optional

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:////data/app.db")
WEBHOOK_SECRET: Optional[str] = os.getenv("WEBHOOK_SECRET")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
