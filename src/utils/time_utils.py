"""
Zaman yardımcıları - Türkçe Lokalizasyon.
Europe/Istanbul (GMT+3) zaman dilimi kullanır.
"""

import os
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

# Oyun zaman dilimi
GAME_TZ = ZoneInfo(os.getenv("TIMEZONE", "Europe/Istanbul"))

# Sıfırlama saatleri
DAILY_RESET_HOUR = int(os.getenv("DAILY_RESET_HOUR", "4"))
DAILY_RESET_MINUTE = int(os.getenv("DAILY_RESET_MINUTE", "0"))
WEEKLY_RESET_DAY = int(os.getenv("WEEKLY_RESET_DAY", "0"))  # 0 = Pazartesi


def now() -> datetime:
    """Oyun zaman diliminde şu anki zaman."""
    return datetime.now(GAME_TZ)


def format_duration(minutes: int) -> str:
    """
    Dakikayı okunabilir Türkçe formata çevir.
    
    Örnekler:
        60 -> "1 saat"
        90 -> "1 saat 30 dakika"
        1440 -> "1 gün"
        4680 -> "3 gün 6 saat"
    """
    if minutes < 60:
        return f"{minutes} dk"
    
    days = minutes // 1440
    remaining = minutes % 1440
    hours = remaining // 60
    mins = remaining % 60
    
    parts = []
    if days > 0:
        parts.append(f"{days} gün")
    if hours > 0:
        parts.append(f"{hours} saat")
    if mins > 0 and days == 0:
        parts.append(f"{mins} dk")
    
    return " ".join(parts)


def format_time_remaining(target_time: datetime) -> str:
    """Hedef zamana ne kadar kaldığını formatla."""
    current = now()
    
    if target_time <= current:
        return "Şimdi hazır!"
    
    diff = target_time - current
    total_minutes = int(diff.total_seconds() / 60)
    
    return format_duration(total_minutes)


def get_next_daily_reset() -> datetime:
    """Sonraki günlük sıfırlama zamanı (04:00)."""
    current = now()
    reset_time = current.replace(
        hour=DAILY_RESET_HOUR, 
        minute=DAILY_RESET_MINUTE, 
        second=0, 
        microsecond=0
    )
    
    if current >= reset_time:
        reset_time += timedelta(days=1)
    
    return reset_time


def get_last_daily_reset() -> datetime:
    """En son günlük sıfırlama zamanı."""
    current = now()
    reset_time = current.replace(
        hour=DAILY_RESET_HOUR,
        minute=DAILY_RESET_MINUTE,
        second=0,
        microsecond=0
    )
    
    if current < reset_time:
        reset_time -= timedelta(days=1)
    
    return reset_time


def get_next_weekly_reset() -> datetime:
    """Sonraki haftalık sıfırlama zamanı (Pazartesi 04:00)."""
    current = now()
    
    days_until_monday = (WEEKLY_RESET_DAY - current.weekday()) % 7
    
    next_monday = current + timedelta(days=days_until_monday)
    reset_time = next_monday.replace(
        hour=DAILY_RESET_HOUR,
        minute=DAILY_RESET_MINUTE,
        second=0,
        microsecond=0
    )
    
    if days_until_monday == 0 and current >= reset_time:
        reset_time += timedelta(days=7)
    
    return reset_time


def get_last_weekly_reset() -> datetime:
    """En son haftalık sıfırlama zamanı."""
    current = now()
    
    days_since_monday = (current.weekday() - WEEKLY_RESET_DAY) % 7
    
    last_monday = current - timedelta(days=days_since_monday)
    reset_time = last_monday.replace(
        hour=DAILY_RESET_HOUR,
        minute=DAILY_RESET_MINUTE,
        second=0,
        microsecond=0
    )
    
    if days_since_monday == 0 and current < reset_time:
        reset_time -= timedelta(days=7)
    
    return reset_time


def get_weekly_reminder_days() -> list[int]:
    """Haftalık hatırlatma günleri: Çarşamba, Cuma, Pazar"""
    return [2, 4, 6]


def should_remind_weekly_today() -> bool:
    """Bugün hatırlatma günü mü?"""
    return now().weekday() in get_weekly_reminder_days()


def get_weekly_urgency_message() -> str:
    """Haftalık reset'e ne kadar kaldığına göre aciliyet mesajı."""
    current = now()
    day = current.weekday()
    
    if day == 2:  # Çarşamba
        return "📋 Hatırlatma: Haftalık görevler 5 gün sonra sıfırlanıyor"
    elif day == 4:  # Cuma
        return "⏰ Dikkat: Haftalık görevler 3 gün sonra sıfırlanıyor"
    elif day == 6:  # Pazar
        return "⚠️ SON ŞANS! Haftalık görevler yarın 04:00'da sıfırlanıyor!"
    else:
        next_reset = get_next_weekly_reset()
        remaining = format_time_remaining(next_reset)
        return f"📋 Haftalık reset: {remaining} kaldı"
