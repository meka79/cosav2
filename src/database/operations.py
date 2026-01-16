"""
Database CRUD Operations - SQLAlchemy ORM with PostgreSQL.
Uses FORCED NAIVE datetime strategy from timers.py.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict

from src.database.models import (
    SessionLocal, Category, Task, TaskStatus, Setting,
    get_setting, get_db_session
)
from src.utils.time_utils import format_duration
from src.scheduler.timers import get_current_time_naive, to_naive_datetime



# =============================================================================
# Category Operations
# =============================================================================

def get_all_categories(include_inactive: bool = False) -> List[Dict]:
    """Tüm kategorileri al."""
    session = get_db_session()
    if not session:
        return []
    
    try:
        query = session.query(Category)
        if not include_inactive:
            query = query.filter(Category.is_active == True)
        
        categories = query.order_by(Category.id).all()
        return [_category_to_dict(c) for c in categories]
    except Exception as e:
        print(f"Kategori listesi hatası: {e}")
        return []
    finally:
        session.close()


def get_category_by_id(category_id: int) -> Optional[Dict]:
    """ID ile kategori al."""
    session = get_db_session()
    if not session:
        return None
    
    try:
        cat = session.query(Category).filter_by(id=category_id).first()
        return _category_to_dict(cat) if cat else None
    finally:
        session.close()


def get_category_by_channel_id(channel_id: str) -> Optional[Dict]:
    """Discord kanal ID'si ile kategori bul (PostgreSQL)."""
    session = get_db_session()
    if not session:
        return None
    
    try:
        # PostgreSQL string karşılaştırması
        cat = session.query(Category).filter(
            Category.discord_channel_id == channel_id,
            Category.is_active == True
        ).first()
        
        if cat:
            print(f"✅ PostgreSQL: Kategori bulundu - {cat.name} (kanal: {channel_id})")
            return _category_to_dict(cat)
        
        print(f"⚠️ PostgreSQL: Kategori bulunamadı (kanal: {channel_id})")
        return None
    except Exception as e:
        print(f"❌ PostgreSQL sorgu hatası: {e}")
        return None
    finally:
        session.close()


def add_category(name: str, description: str, reset_type: str) -> int:
    """Yeni kategori ekle."""
    session = get_db_session()
    if not session:
        return -1
    
    try:
        cat = Category(name=name, description=description, reset_type=reset_type)
        session.add(cat)
        session.commit()
        return cat.id
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def update_category(
    category_id: int,
    name: str,
    description: str,
    reset_type: str,
    is_active: bool = True,
    pre_notify_minutes: int = 0,
    show_resource_reminder: bool = False
) -> bool:
    """Kategoriyi güncelle."""
    session = get_db_session()
    if not session:
        return False
    
    try:
        cat = session.query(Category).filter_by(id=category_id).first()
        if not cat:
            return False
        
        cat.name = name
        cat.description = description
        cat.reset_type = reset_type
        cat.is_active = is_active
        cat.pre_notify_minutes = pre_notify_minutes
        cat.show_resource_reminder = show_resource_reminder
        
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"Kategori güncelleme hatası: {e}")
        return False
    finally:
        session.close()


def set_category_channel(category_id: int, channel_id: str) -> bool:
    """Kategori için Discord kanalı ayarla."""
    session = get_db_session()
    if not session:
        return False
    
    try:
        cat = session.query(Category).filter_by(id=category_id).first()
        if cat:
            cat.discord_channel_id = channel_id
            session.commit()
            return True
        return False
    except:
        session.rollback()
        return False
    finally:
        session.close()


def set_category_active(category_id: int, is_active: bool) -> bool:
    """Kategori aktiflik durumunu değiştir."""
    session = get_db_session()
    if not session:
        return False
    
    try:
        cat = session.query(Category).filter_by(id=category_id).first()
        if cat:
            cat.is_active = is_active
            session.commit()
            return True
        return False
    except:
        session.rollback()
        return False
    finally:
        session.close()


def delete_category(category_id: int) -> bool:
    """Kategoriyi sil."""
    session = get_db_session()
    if not session:
        return False
    
    try:
        cat = session.query(Category).filter_by(id=category_id).first()
        if cat:
            session.delete(cat)
            session.commit()
            return True
        return False
    except:
        session.rollback()
        return False
    finally:
        session.close()


def _category_to_dict(cat: Category) -> Dict:
    """Category objesini dict'e çevir."""
    if not cat:
        return {}
    return {
        "id": cat.id,
        "name": cat.name,
        "description": cat.description,
        "reset_type": cat.reset_type,
        "discord_channel_id": cat.discord_channel_id,
        "is_active": cat.is_active,
        "pre_notify_minutes": cat.pre_notify_minutes,
        "show_resource_reminder": cat.show_resource_reminder,
        "created_at": cat.created_at.isoformat() if cat.created_at else None,
    }


# =============================================================================
# Task Operations
# =============================================================================

def get_all_tasks(include_inactive_categories: bool = False) -> List[Dict]:
    """Tüm görevleri al."""
    session = get_db_session()
    if not session:
        return []
    
    try:
        query = session.query(Task).join(Category).filter(Task.is_active == True)
        
        if not include_inactive_categories:
            query = query.filter(Category.is_active == True)
        
        tasks = query.order_by(Category.id, Task.name).all()
        return [_task_to_dict(t) for t in tasks]
    except Exception as e:
        print(f"Görev listesi hatası: {e}")
        return []
    finally:
        session.close()


def get_tasks_by_category(category_id: int) -> List[Dict]:
    """Kategorideki görevleri al."""
    session = get_db_session()
    if not session:
        return []
    
    try:
        tasks = session.query(Task).filter_by(
            category_id=category_id, 
            is_active=True
        ).order_by(Task.name).all()
        return [_task_to_dict(t) for t in tasks]
    finally:
        session.close()


def get_task_by_id(task_id: int) -> Optional[Dict]:
    """ID ile görev al."""
    session = get_db_session()
    if not session:
        return None
    
    try:
        task = session.query(Task).filter_by(id=task_id).first()
        return _task_to_dict(task) if task else None
    finally:
        session.close()


def add_task(
    category_id: int,
    name: str,
    description: str = "",
    cooldown_minutes: int = 0,
    active_duration_minutes: int = 0
) -> int:
    """Yeni görev ekle."""
    session = get_db_session()
    if not session:
        return -1
    
    try:
        task = Task(
            category_id=category_id,
            name=name,
            description=description,
            cooldown_minutes=cooldown_minutes,
            active_duration_minutes=active_duration_minutes
        )
        session.add(task)
        session.flush()
        
        # Durum kaydı oluştur
        status = TaskStatus(task_id=task.id, last_status="initialized")
        session.add(status)
        
        session.commit()
        return task.id
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def update_task(
    task_id: int,
    name: str,
    description: str,
    cooldown_minutes: int,
    active_duration_minutes: int
) -> bool:
    """Görevi güncelle."""
    session = get_db_session()
    if not session:
        return False
    
    try:
        task = session.query(Task).filter_by(id=task_id).first()
        if not task:
            return False
        
        task.name = name
        task.description = description
        task.cooldown_minutes = cooldown_minutes
        task.active_duration_minutes = active_duration_minutes
        
        session.commit()
        return True
    except:
        session.rollback()
        return False
    finally:
        session.close()


def delete_task(task_id: int) -> bool:
    """Görevi sil."""
    return hard_delete_task(task_id)


def hard_delete_task(task_id: int) -> bool:
    """Görevi kalıcı olarak sil."""
    session = get_db_session()
    if not session:
        return False
    
    try:
        task = session.query(Task).filter_by(id=task_id).first()
        if task:
            session.delete(task)
            session.commit()
            return True
        return False
    except:
        session.rollback()
        return False
    finally:
        session.close()


def _task_to_dict(task: Task) -> Dict:
    """Task objesini dict'e çevir."""
    if not task:
        return {}
    
    cat = task.category
    status = task.status
    
    result = {
        "id": task.id,
        "category_id": task.category_id,
        "name": task.name,
        "description": task.description,
        "cooldown_minutes": task.cooldown_minutes,
        "active_duration_minutes": task.active_duration_minutes,
        "is_active": task.is_active,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        # Category info
        "category_name": cat.name if cat else "Bilinmeyen",
        "reset_type": cat.reset_type if cat else "unknown",
        "discord_channel_id": cat.discord_channel_id if cat else None,
        "pre_notify_minutes": cat.pre_notify_minutes if cat else 0,
        "show_resource_reminder": cat.show_resource_reminder if cat else False,
    }
    
    # Status info
    if status:
        result.update({
            "is_completed": status.is_completed,
            "last_completed_at": status.last_completed_at.isoformat() if status.last_completed_at else None,
            "instance_entered_at": status.instance_entered_at.isoformat() if status.instance_entered_at else None,
            "notification_message_id": status.notification_message_id,
            "last_notified_at": status.last_notified_at.isoformat() if status.last_notified_at else None,
            "last_status": status.last_status,
            "pre_notified": status.pre_notified,
        })
    else:
        result.update({
            "is_completed": False,
            "last_completed_at": None,
            "instance_entered_at": None,
            "notification_message_id": None,
            "last_notified_at": None,
            "last_status": "initialized",
            "pre_notified": False,
        })
    
    return result


# =============================================================================
# Status Operations
# =============================================================================

def mark_task_completed(task_id: int) -> bool:
    """Görevi tamamlandı olarak işaretle."""
    session = get_db_session()
    if not session:
        return False
    
    try:
        status = session.query(TaskStatus).filter_by(task_id=task_id).first()
        if status:
            status.is_completed = True
            status.last_completed_at = get_current_time_naive()  # FORCED NAIVE
            status.last_status = "completed"
            status.pre_notified = False
            session.commit()
            return True
        return False
    except:
        session.rollback()
        return False
    finally:
        session.close()


def mark_instance_entered(task_id: int) -> bool:
    """Instance'a girildi olarak işaretle."""
    session = get_db_session()
    if not session:
        return False
    
    try:
        status = session.query(TaskStatus).filter_by(task_id=task_id).first()
        if status:
            current = get_current_time_naive()  # FORCED NAIVE
            status.instance_entered_at = current
            status.last_completed_at = current
            status.last_status = "entered"
            status.pre_notified = False
            session.commit()
            return True
        return False
    except:
        session.rollback()
        return False
    finally:
        session.close()


def reset_daily_tasks() -> int:
    """Günlük görevleri sıfırla."""
    session = get_db_session()
    if not session:
        return 0
    
    try:
        count = 0
        tasks = session.query(Task).join(Category).filter(
            Category.reset_type == "daily",
            Task.is_active == True,
            Category.is_active == True
        ).all()
        
        for task in tasks:
            if task.status:
                task.status.is_completed = False
                task.status.last_status = "reset"
                task.status.pre_notified = False
                count += 1
        
        session.commit()
        return count
    except:
        session.rollback()
        return 0
    finally:
        session.close()


def reset_weekly_tasks() -> int:
    """Haftalık görevleri sıfırla."""
    session = get_db_session()
    if not session:
        return 0
    
    try:
        count = 0
        tasks = session.query(Task).join(Category).filter(
            Category.reset_type == "weekly",
            Task.is_active == True,
            Category.is_active == True
        ).all()
        
        for task in tasks:
            if task.status:
                task.status.is_completed = False
                task.status.last_status = "reset"
                task.status.pre_notified = False
                count += 1
        
        session.commit()
        return count
    except:
        session.rollback()
        return 0
    finally:
        session.close()


def update_notification_sent(task_id: int, message_id: str, status_text: str) -> bool:
    """Bildirim gönderildi olarak güncelle - DEBUG LOGGING."""
    session = get_db_session()
    if not session:
        print(f"❌ NOTIFICATION UPDATE FAILED: No database session for task {task_id}")
        return False
    
    try:
        status = session.query(TaskStatus).filter_by(task_id=task_id).first()
        if status:
            current_time = get_current_time_naive()
            print(f"📝 Updating notification for task {task_id}: message_id={message_id}, time={current_time}")
            
            status.notification_message_id = message_id
            status.last_notified_at = current_time
            status.last_status = status_text
            session.commit()
            
            print(f"✅ NOTIFICATION UPDATE SUCCESS: task {task_id}")
            return True
        else:
            print(f"❌ NOTIFICATION UPDATE FAILED: TaskStatus not found for task {task_id}")
            return False
    except Exception as e:
        session.rollback()
        print(f"❌ NOTIFICATION UPDATE FAILED: {e}")
        print(f"   Task ID: {task_id}, Message ID: {message_id}, Status: {status_text}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()


def mark_pre_notified(task_id: int) -> bool:
    """Ön bildirim gönderildi olarak işaretle."""
    session = get_db_session()
    if not session:
        return False
    
    try:
        status = session.query(TaskStatus).filter_by(task_id=task_id).first()
        if status:
            status.pre_notified = True
            session.commit()
            return True
        return False
    except:
        session.rollback()
        return False
    finally:
        session.close()


def update_task_last_status(task_id: int, status_text: str) -> bool:
    """Görev durumunu güncelle."""
    session = get_db_session()
    if not session:
        return False
    
    try:
        status = session.query(TaskStatus).filter_by(task_id=task_id).first()
        if status:
            status.last_status = status_text
            session.commit()
            return True
        return False
    except:
        session.rollback()
        return False
    finally:
        session.close()


def get_task_by_message_id(message_id: str) -> Optional[Dict]:
    """Mesaj ID'si ile görevi bul."""
    session = get_db_session()
    if not session:
        return None
    
    try:
        status = session.query(TaskStatus).filter_by(notification_message_id=message_id).first()
        if status and status.task:
            return _task_to_dict(status.task)
        return None
    finally:
        session.close()


def get_stale_notifications(stale_minutes: int = 60) -> List[Dict]:
    """Eski bildirimleri al - FORCED NAIVE."""
    session = get_db_session()
    if not session:
        return []
    
    try:
        cutoff = get_current_time_naive() - timedelta(minutes=stale_minutes)  # FORCED NAIVE
        
        statuses = session.query(TaskStatus).join(Task).join(Category).filter(
            TaskStatus.last_notified_at < cutoff,
            TaskStatus.last_status == "notified",
            TaskStatus.notification_message_id != None,
            Task.is_active == True,
            Category.is_active == True
        ).all()
        
        return [_task_to_dict(s.task) for s in statuses if s.task]
    except:
        return []
    finally:
        session.close()


# =============================================================================
# Status Calculation
# =============================================================================

def get_task_with_status(task: Dict) -> Dict:
    """
    Göreve hesaplanmış durum ekle.
    timers.py FORCED NAIVE strateji kullanır - tüm timezone bilgisi kaldırılır.
    """
    from src.scheduler.timers import get_task_status, TaskState
    
    # Pass raw values - timers.py converts everything to naive datetimes
    # Handles: None, datetime object, or ISO string from PostgreSQL
    status = get_task_status(
        reset_type=task.get("reset_type", "daily"),
        is_completed=bool(task.get("is_completed", False)),
        last_completed_at=task.get("last_completed_at"),
        instance_entered_at=task.get("instance_entered_at"),
        cooldown_minutes=task.get("cooldown_minutes", 0),
        active_duration_minutes=task.get("active_duration_minutes", 0)
    )
    
    result = dict(task)
    result["status"] = status
    result["status_emoji"] = status.emoji
    result["status_message"] = status.message
    result["is_available"] = status.is_available
    result["is_open"] = status.is_open
    result["current_state"] = status.state.value
    result["available_at"] = status.available_at
    
    return result



def get_all_tasks_with_status() -> List[Dict]:
    """Tüm görevleri durum bilgisiyle al."""
    tasks = get_all_tasks()
    return [get_task_with_status(t) for t in tasks]


def get_tasks_needing_notification() -> List[Dict]:
    """
    Bildirim gereken görevleri al.
    FORCED NAIVE datetime kullanır - spam önlenir.
    """
    tasks = get_all_tasks_with_status()
    current = get_current_time_naive()  # FORCED NAIVE
    
    try:
        cooldown = int(get_setting("notification_cooldown_minutes", "120"))
    except:
        cooldown = 120
    
    result = []
    
    for task in tasks:
        if not (task.get("is_available") or task.get("is_open")):
            continue
        
        state = task.get("current_state", "")
        last_status = task.get("last_status", "")
        
        # Check notification cooldown with FORCED NAIVE
        last_notified = task.get("last_notified_at")
        if last_notified:
            last_dt = to_naive_datetime(last_notified)  # FORCED NAIVE
            if last_dt:
                mins = (current - last_dt).total_seconds() / 60
                if mins < cooldown and last_status in ["notified", state]:
                    continue
        
        if last_status == "initialized":
            update_task_last_status(task["id"], state)
            continue
        
        if last_status == "skipped":
            continue
        
        result.append(task)
    
    return result


def get_tasks_needing_pre_notification() -> List[Dict]:
    """
    Ön bildirim gereken görevleri al.
    FORCED NAIVE datetime kullanır.
    """
    tasks = get_all_tasks_with_status()
    current = get_current_time_naive()  # FORCED NAIVE
    
    result = []
    
    for task in tasks:
        if task.get("is_available") or task.get("is_open"):
            continue
        
        if task.get("pre_notified"):
            continue
        
        pre_mins = task.get("pre_notify_minutes", 0)
        if pre_mins <= 0:
            continue
        
        available_at = task.get("available_at")
        if not available_at:
            continue
        
        # Convert available_at to naive for comparison
        available_naive = to_naive_datetime(available_at)
        if not available_naive:
            continue
        
        time_until = (available_naive - current).total_seconds() / 60
        
        if 0 < time_until <= pre_mins:
            result.append(task)
    
    return result


def get_tasks_grouped_by_category() -> Dict[str, List[Dict]]:
    """Bildirim gereken görevleri kategoriye göre grupla."""
    tasks = get_tasks_needing_notification()
    
    grouped = {}
    for task in tasks:
        cat = task.get("category_name", "Bilinmeyen")
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(task)
    
    return grouped


def get_category_channel(category_id: int) -> Optional[str]:
    """Kategori için kanal ID'si al."""
    cat = get_category_by_id(category_id)
    return cat.get("discord_channel_id") if cat else None
