"""
Bot başlatıcı - PostgreSQL destekli.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# DATABASE_URL kontrolü
DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    print("⚠️ UYARI: DATABASE_URL ayarlanmamış!")
    print("Railway veya PostgreSQL kullanıyorsanız bu değişkeni ayarlayın.")

from src.bot.client import run_bot

if __name__ == "__main__":
    run_bot()
