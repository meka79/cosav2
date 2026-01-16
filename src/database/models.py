"""
Database Models - SQLAlchemy ORM with PostgreSQL support.
Includes one-time seed for default categories and tasks.
"""

import os
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from dotenv import load_dotenv

load_dotenv()

# Database URL from environment (Railway provides DATABASE_URL)
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Handle Railway's postgres:// vs postgresql:// format
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine and session
if DATABASE_URL:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    engine = None
    SessionLocal = None

Base = declarative_base()


# =============================================================================
# ORM Models
# =============================================================================

class Category(Base):
    """Kategori modeli."""
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, default="")
    reset_type = Column(String(50), nullable=False)  # daily, weekly, cooldown, instance
    discord_channel_id = Column(String(100), default=None)
    is_active = Column(Boolean, default=True)
    pre_notify_minutes = Column(Integer, default=0)
    show_resource_reminder = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    tasks = relationship("Task", back_populates="category", cascade="all, delete-orphan")


class Task(Base):
    """Görev modeli."""
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    cooldown_minutes = Column(Integer, default=0)
    active_duration_minutes = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    category = relationship("Category", back_populates="tasks")
    status = relationship("TaskStatus", back_populates="task", uselist=False, cascade="all, delete-orphan")


class TaskStatus(Base):
    """Görev durumu modeli."""
    __tablename__ = "task_status"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), unique=True, nullable=False)
    is_completed = Column(Boolean, default=False)
    last_completed_at = Column(DateTime, default=None)
    instance_entered_at = Column(DateTime, default=None)
    notification_message_id = Column(String(100), default=None)
    last_notified_at = Column(DateTime, default=None)
    last_status = Column(String(50), default="initialized")
    pre_notified = Column(Boolean, default=False)
    
    # Relationships
    task = relationship("Task", back_populates="status")


class Setting(Base):
    """Ayarlar modeli."""
    __tablename__ = "settings"
    
    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)


# =============================================================================
# Database Initialization
# =============================================================================

def init_db():
    if not engine:
        print("⚠️ DATABASE_URL ayarlanmamış!")
        return False

    try:
        Base.metadata.create_all(bind=engine)

        session = SessionLocal()
        try:
            category_count = session.query(Category).count()
            if category_count == 0:
                seed_database()
            else:
                print(f"📦 Seed atlandı, {category_count} kategori zaten var.")
        finally:
            session.close()

        return True

    except Exception as e:
        print(f"❌ Veritabanı hatası: {e}")
        return False


def seed_database():
    """
    Varsayılan kategorileri ve görevleri ekle.
    SADECE tablolar boşsa çalışır (one-time seed).
    """
    if not SessionLocal:
        return
    
    session = SessionLocal()
    try:
        # Kategori sayısını kontrol et - zaten veri varsa atla
        category_count = session.query(Category).count()
        if category_count > 0:
            print(f"📦 Veritabanında {category_count} kategori mevcut, seed atlandı.")
            return
        
        print("🌱 Varsayılan veriler ekleniyor...")
        
        # =================================================================
        # VARSAYILAN KATEGORİLER
        # =================================================================
        categories_data = [
            {"name": "Daily Quests", "description": "Günlük görevler", "reset_type": "daily"},
            {"name": "Weekly Quests", "description": "Haftalık görevler", "reset_type": "weekly"},
            {"name": "Altars", "description": "Altar teslimatları (24 saat bekleme)", "reset_type": "cooldown"},
            {"name": "Repeatable Quests", "description": "Tekrarlanabilir görevler", "reset_type": "cooldown"},
            {"name": "Instances", "description": "Instance'lar (açık kalma + bekleme)", "reset_type": "instance"},
            {"name": "Farming Instances", "description": "Farm instance'ları", "reset_type": "instance"},
            {"name": "Events", "description": "Etkinlikler", "reset_type": "cooldown"},
        ]
        
        category_map = {}
        for cat_data in categories_data:
            cat = Category(**cat_data)
            session.add(cat)
            session.flush()  # ID almak için
            category_map[cat_data["name"]] = cat.id
        
        # =================================================================
        # VARSAYILAN GÖREVLER
        # =================================================================
        tasks_data = [
            # Daily Quests
            {"category": "Daily Quests", "name": "Mystras Daily Quest", "description": "Mystras günlük görevi", "cooldown": 0, "active": 0},
            {"category": "Daily Quests", "name": "Battle Pass Daily", "description": "Battle Pass günlük görev", "cooldown": 0, "active": 0},
            {"category": "Daily Quests", "name": "Guild Daily Quest", "description": "Lonca günlük görevi", "cooldown": 0, "active": 0},
            
            # Weekly Quests
            {"category": "Weekly Quests", "name": "Battle Pass Weekly", "description": "Battle Pass haftalık görev", "cooldown": 0, "active": 0},
            {"category": "Weekly Quests", "name": "Guild Weekly Quest", "description": "Lonca haftalık görevi", "cooldown": 0, "active": 0},
            
            # Altars (24 saat = 1440 dakika)
            {"category": "Altars", "name": "Dragon Altar", "description": "Ejderha altarı", "cooldown": 1440, "active": 0},
            {"category": "Altars", "name": "Dead Altar", "description": "Ölü altarı", "cooldown": 1440, "active": 0},
            {"category": "Altars", "name": "Fire Altar", "description": "Ateş altarı", "cooldown": 1440, "active": 0},
            
            # Repeatable Quests
            {"category": "Repeatable Quests", "name": "Mystras Reputation", "description": "Mystras itibar görevi", "cooldown": 180, "active": 0},
            {"category": "Repeatable Quests", "name": "Farming Quest", "description": "Farm görevi", "cooldown": 60, "active": 0},
            
            # Instances (cooldown = bekleme, active = açık kalma süresi)
            {"category": "Instances", "name": "Zigred Hive", "description": "3 gün bekleme, 6 saat açık", "cooldown": 4320, "active": 360},
            {"category": "Instances", "name": "Guaryld Korr", "description": "4 gün bekleme, 12 saat açık", "cooldown": 5760, "active": 720},
            {"category": "Instances", "name": "Kargath Expedition", "description": "2 gün bekleme, 4 saat açık", "cooldown": 2880, "active": 240},
            
            # Farming Instances
            {"category": "Farming Instances", "name": "Gold Farm Instance", "description": "Altın farm instance", "cooldown": 1440, "active": 120},
            {"category": "Farming Instances", "name": "Material Farm Instance", "description": "Malzeme farm instance", "cooldown": 720, "active": 60},
            
            # Events
            {"category": "Events", "name": "World Boss", "description": "Dünya boss'u", "cooldown": 360, "active": 0},
            {"category": "Events", "name": "Arena Season", "description": "Arena sezonu", "cooldown": 1440, "active": 0},
        ]
        
        for task_data in tasks_data:
            cat_name = task_data["category"]
            if cat_name not in category_map:
                continue
            
            task = Task(
                category_id=category_map[cat_name],
                name=task_data["name"],
                description=task_data["description"],
                cooldown_minutes=task_data["cooldown"],
                active_duration_minutes=task_data["active"]
            )
            session.add(task)
            session.flush()
            
            # Her görev için status kaydı oluştur
            status = TaskStatus(task_id=task.id, last_status="available")
            session.add(status)
        
        # =================================================================
        # VARSAYILAN AYARLAR
        # =================================================================
        settings_data = [
            ("discord_parent_category_id", ""),
            ("notification_cooldown_minutes", "120"),
            ("bot_active", "true"),
            ("auto_refresh_minutes", "60"),
        ]
        
        for key, val in settings_data:
            setting = Setting(key=key, value=val)
            session.add(setting)
        
        session.commit()
        
        task_count = session.query(Task).count()
        print(f"✅ Seed tamamlandı: {len(categories_data)} kategori, {task_count} görev eklendi!")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Seed hatası: {e}")
    finally:
        session.close()


# =============================================================================
# Settings Helpers
# =============================================================================

def get_setting(key: str, default: str = "") -> str:
    """Ayar değerini al."""
    if not SessionLocal:
        return default
    
    session = SessionLocal()
    try:
        setting = session.query(Setting).filter_by(key=key).first()
        return setting.value if setting else default
    except:
        return default
    finally:
        session.close()


def set_setting(key: str, value: str) -> None:
    """Ayar değerini kaydet."""
    if not SessionLocal:
        return
    
    session = SessionLocal()
    try:
        setting = session.query(Setting).filter_by(key=key).first()
        if setting:
            setting.value = value
        else:
            setting = Setting(key=key, value=value)
            session.add(setting)
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Ayar kaydetme hatası: {e}")
    finally:
        session.close()


def is_bot_active() -> bool:
    """Bot aktif mi?"""
    return get_setting("bot_active", "true").lower() == "true"


def set_bot_active(active: bool) -> None:
    """Bot durumunu ayarla."""
    set_setting("bot_active", "true" if active else "false")


def get_db_session():
    """Veritabanı oturumu al."""
    if not SessionLocal:
        return None
    return SessionLocal()

