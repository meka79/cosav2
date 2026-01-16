"""
Timer calculations for cooldown-based and instance-based tasks.
FORCED NAIVE COMPARISON STRATEGY - strips timezone info before comparing.
Works on all environments: local, Railway, PostgreSQL.
"""

from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union
import os

from dotenv import load_dotenv

load_dotenv()

# Get timezone offset for Istanbul (UTC+3)
ISTANBUL_OFFSET = timedelta(hours=3)


class TaskState(Enum):
    """Possible states for a task."""
    AVAILABLE = "available"
    COMPLETED = "completed"
    ON_COOLDOWN = "on_cooldown"
    INSTANCE_OPEN = "open"
    UNKNOWN = "unknown"


@dataclass
class TaskStatus:
    """Status information for a task."""
    state: TaskState
    message: str
    available_at: Optional[datetime] = None
    closes_at: Optional[datetime] = None
    time_remaining: Optional[str] = None
    
    @property
    def is_available(self) -> bool:
        return self.state == TaskState.AVAILABLE
    
    @property
    def is_open(self) -> bool:
        return self.state == TaskState.INSTANCE_OPEN
    
    @property
    def emoji(self) -> str:
        return {
            TaskState.AVAILABLE: "🟢",
            TaskState.COMPLETED: "✅",
            TaskState.ON_COOLDOWN: "🔴",
            TaskState.INSTANCE_OPEN: "🔓",
            TaskState.UNKNOWN: "❓",
        }.get(self.state, "❓")


def get_current_time_naive() -> datetime:
    """
    Get current time in Istanbul timezone as NAIVE datetime.
    This is the safest approach for cross-environment compatibility.
    """
    # Get UTC now, add Istanbul offset, strip timezone info
    utc_now = datetime.now(timezone.utc)
    istanbul_now = utc_now + ISTANBUL_OFFSET
    return istanbul_now.replace(tzinfo=None)


def to_naive_datetime(dt: Optional[Union[datetime, str]]) -> Optional[datetime]:
    """
    Convert any datetime input to a NAIVE datetime in Istanbul timezone.
    Handles: None, naive datetime, aware datetime, ISO string.
    
    STRATEGY: Convert everything to naive for safe comparison.
    """
    if dt is None:
        return None
    
    # Debug logging for Railway
    print(f"🔍 to_naive_datetime input: {type(dt).__name__} = {dt}")
    
    # Handle string input (ISO format from PostgreSQL)
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except (ValueError, TypeError) as e:
            print(f"⚠️ String parse failed: {e}")
            return None
    
    # Ensure it's a datetime
    if not isinstance(dt, datetime):
        print(f"⚠️ Not a datetime after parsing: {type(dt)}")
        return None
    
    # If aware, convert to UTC then to Istanbul, then strip tzinfo
    if dt.tzinfo is not None:
        try:
            # Convert to UTC first
            utc_dt = dt.astimezone(timezone.utc)
            # Add Istanbul offset
            istanbul_dt = utc_dt + ISTANBUL_OFFSET
            # Return as naive
            result = istanbul_dt.replace(tzinfo=None)
            print(f"✅ Aware -> Naive Istanbul: {result}")
            return result
        except Exception as e:
            print(f"⚠️ Timezone conversion failed: {e}")
            # Fallback: just strip tzinfo
            return dt.replace(tzinfo=None)
    
    # Already naive - assume it's already in Istanbul time
    print(f"✅ Already naive: {dt}")
    return dt


def format_time_remaining(target_time: Optional[datetime]) -> str:
    """Format time remaining until target (both as naive datetimes)."""
    if target_time is None:
        return "Bilinmiyor"
    
    current = get_current_time_naive()
    target = to_naive_datetime(target_time)
    
    if target is None:
        return "Hesaplanamadı"
    
    if current >= target:
        return "Şimdi hazır!"
    
    diff = target - current
    total_minutes = int(diff.total_seconds() / 60)
    
    if total_minutes < 60:
        return f"{total_minutes} dk"
    
    days = total_minutes // 1440
    remaining = total_minutes % 1440
    hours = remaining // 60
    mins = remaining % 60
    
    parts = []
    if days > 0:
        parts.append(f"{days} gün")
    if hours > 0:
        parts.append(f"{hours} saat")
    if mins > 0 and days == 0:
        parts.append(f"{mins} dk")
    
    return " ".join(parts) if parts else "Biraz kaldı"


def calculate_cooldown_status(
    last_completed_at: Optional[Union[datetime, str]],
    cooldown_minutes: int
) -> TaskStatus:
    """
    Calculate status for a cooldown-based task.
    FORCED NAIVE COMPARISON - guaranteed to work everywhere.
    """
    # Get current time as NAIVE
    current_naive = get_current_time_naive()
    
    print(f"📊 calculate_cooldown_status:")
    print(f"   current_naive = {current_naive} (type: {type(current_naive).__name__})")
    print(f"   last_completed_at = {last_completed_at} (type: {type(last_completed_at).__name__ if last_completed_at else 'None'})")
    
    # Never completed = available
    if last_completed_at is None:
        return TaskStatus(
            state=TaskState.AVAILABLE,
            message="Hiç tamamlanmadı - Hemen yapılabilir!"
        )
    
    # Convert to NAIVE datetime
    last_completed_naive = to_naive_datetime(last_completed_at)
    
    if last_completed_naive is None:
        print("⚠️ Could not parse last_completed_at, assuming available")
        return TaskStatus(
            state=TaskState.AVAILABLE,
            message="Tarih okunamadı - Yapılabilir"
        )
    
    # Calculate availability (NAIVE datetime)
    available_at_naive = last_completed_naive + timedelta(minutes=cooldown_minutes)
    
    print(f"   last_completed_naive = {last_completed_naive}")
    print(f"   available_at_naive = {available_at_naive}")
    print(f"   current_naive >= available_at_naive = {current_naive >= available_at_naive}")
    
    # FORCED NAIVE COMPARISON - LINE 87 IS NOW SAFE
    if current_naive >= available_at_naive:
        return TaskStatus(
            state=TaskState.AVAILABLE,
            message="Hazır!",
            available_at=available_at_naive
        )
    else:
        time_remaining = format_time_remaining(available_at_naive)
        return TaskStatus(
            state=TaskState.ON_COOLDOWN,
            message=f"{time_remaining} sonra hazır",
            available_at=available_at_naive,
            time_remaining=time_remaining
        )


def calculate_instance_status(
    instance_entered_at: Optional[Union[datetime, str]],
    active_duration_minutes: int,
    cooldown_minutes: int
) -> TaskStatus:
    """
    Calculate status for an instance-type task.
    FORCED NAIVE COMPARISON.
    """
    current_naive = get_current_time_naive()
    
    if instance_entered_at is None:
        return TaskStatus(
            state=TaskState.AVAILABLE,
            message="Hiç girilmedi - Girilebilir!"
        )
    
    # Convert to NAIVE
    entered_naive = to_naive_datetime(instance_entered_at)
    
    if entered_naive is None:
        return TaskStatus(
            state=TaskState.AVAILABLE,
            message="Tarih okunamadı - Girilebilir"
        )
    
    # Calculate timestamps (all NAIVE)
    close_time_naive = entered_naive + timedelta(minutes=active_duration_minutes)
    available_at_naive = close_time_naive + timedelta(minutes=cooldown_minutes)
    
    # FORCED NAIVE COMPARISONS
    if current_naive < close_time_naive:
        time_remaining = format_time_remaining(close_time_naive)
        return TaskStatus(
            state=TaskState.INSTANCE_OPEN,
            message=f"AÇIK - {time_remaining} sonra kapanacak",
            available_at=available_at_naive,
            closes_at=close_time_naive,
            time_remaining=time_remaining
        )
    elif current_naive < available_at_naive:
        time_remaining = format_time_remaining(available_at_naive)
        return TaskStatus(
            state=TaskState.ON_COOLDOWN,
            message=f"Kapalı - {time_remaining} sonra açılacak",
            available_at=available_at_naive,
            time_remaining=time_remaining
        )
    else:
        return TaskStatus(
            state=TaskState.AVAILABLE,
            message="Girilebilir!",
            available_at=available_at_naive
        )


def calculate_daily_status(is_completed: bool) -> TaskStatus:
    """Calculate status for a daily reset task."""
    current_naive = get_current_time_naive()
    reset_hour = int(os.getenv("DAILY_RESET_HOUR", "4"))
    reset_minute = int(os.getenv("DAILY_RESET_MINUTE", "0"))
    
    # Calculate next reset (NAIVE)
    next_reset = current_naive.replace(hour=reset_hour, minute=reset_minute, second=0, microsecond=0)
    if current_naive >= next_reset:
        next_reset += timedelta(days=1)
    
    if is_completed:
        time_remaining = format_time_remaining(next_reset)
        return TaskStatus(
            state=TaskState.COMPLETED,
            message=f"Bugün tamamlandı! {time_remaining} sonra sıfırlanacak",
            available_at=next_reset,
            time_remaining=time_remaining
        )
    else:
        return TaskStatus(
            state=TaskState.AVAILABLE,
            message="Bugün yapılmadı"
        )


def calculate_weekly_status(is_completed: bool) -> TaskStatus:
    """Calculate status for a weekly reset task."""
    current_naive = get_current_time_naive()
    reset_hour = int(os.getenv("DAILY_RESET_HOUR", "4"))
    reset_minute = int(os.getenv("DAILY_RESET_MINUTE", "0"))
    reset_day = int(os.getenv("WEEKLY_RESET_DAY", "0"))  # Monday = 0
    
    # Find next Monday reset (NAIVE)
    days_until = (reset_day - current_naive.weekday()) % 7
    next_reset = current_naive + timedelta(days=days_until)
    next_reset = next_reset.replace(hour=reset_hour, minute=reset_minute, second=0, microsecond=0)
    
    if days_until == 0 and current_naive >= next_reset:
        next_reset += timedelta(days=7)
    
    time_remaining = format_time_remaining(next_reset)
    
    if is_completed:
        return TaskStatus(
            state=TaskState.COMPLETED,
            message=f"Bu hafta tamamlandı! {time_remaining} sonra sıfırlanacak",
            available_at=next_reset,
            time_remaining=time_remaining
        )
    else:
        day = current_naive.weekday()
        urgency = "⚠️ SON GÜN!" if day == 6 else (f"⏰ {7 - day} gün kaldı" if day >= 4 else "")
        return TaskStatus(
            state=TaskState.AVAILABLE,
            message=f"Bu hafta yapılmadı. {urgency}".strip(),
            available_at=next_reset
        )


def get_task_status(
    reset_type: str,
    is_completed: bool = False,
    last_completed_at: Optional[Union[datetime, str]] = None,
    instance_entered_at: Optional[Union[datetime, str]] = None,
    cooldown_minutes: int = 0,
    active_duration_minutes: int = 0
) -> TaskStatus:
    """
    Universal function to get task status.
    All datetime comparisons use FORCED NAIVE strategy.
    """
    if reset_type == 'daily':
        return calculate_daily_status(is_completed)
    
    elif reset_type == 'weekly':
        return calculate_weekly_status(is_completed)
    
    elif reset_type == 'cooldown':
        return calculate_cooldown_status(last_completed_at, cooldown_minutes)
    
    elif reset_type == 'instance':
        return calculate_instance_status(
            instance_entered_at, 
            active_duration_minutes, 
            cooldown_minutes
        )
    
    else:
        return TaskStatus(
            state=TaskState.UNKNOWN,
            message=f"Bilinmeyen reset tipi: {reset_type}"
        )
