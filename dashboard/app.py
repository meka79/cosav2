"""
Dashboard Ana Uygulama - PostgreSQL destekli.
"""

import streamlit as st
import sys
import os
from pathlib import Path

# src klasörünü path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

# DATABASE_URL kontrolü (EN ÖNCE)
DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    st.error("⚠️ DATABASE_URL ayarlanmamış!")
    st.info(
        "Railway veya başka bir PostgreSQL servisi kullanıyorsanız, "
        "DATABASE_URL environment variable'ı ayarlanmalı."
    )
    st.code("DATABASE_URL=postgresql://user:password@host:port/database")
    st.stop()

# 🔥 VERİTABANI BAŞLAT (TABLOLAR + SEED) — SADECE 1 KERE
from src.database.models import init_db
init_db()

st.set_page_config(
    page_title="War of Dragons - Görev Takipçisi",
    page_icon="🐉",
    layout="wide"
)


def main():
    """Ana uygulama."""
    
    # Sidebar navigasyon
    st.sidebar.title("🐉 Görev Takipçisi")
    st.sidebar.write("---")
    
    page = st.sidebar.radio(
        "Navigasyon",
        ["📊 Durum", "📋 Görevler", "📁 Kategoriler", "⚙️ Ayarlar"],
        label_visibility="collapsed"
    )
    
    st.sidebar.write("---")
    st.sidebar.caption("War of Dragons")
    st.sidebar.caption("Görev Takip Sistemi")
    
    if page == "📊 Durum":
        show_status_page()
    elif page == "📋 Görevler":
        show_tasks_page()
    elif page == "📁 Kategoriler":
        show_categories_page()
    elif page == "⚙️ Ayarlar":
        show_settings_page()



def show_status_page():
    """Durum sayfası."""
    from dashboard.pages.status import show
    show()


def show_tasks_page():
    """Görevler sayfası."""
    from dashboard.pages.tasks import show
    show()


def show_categories_page():
    """Kategoriler sayfası."""
    from dashboard.pages.categories import show
    show()


def show_settings_page():
    """Ayarlar sayfası."""
    from src.database.operations import reset_daily_tasks, reset_weekly_tasks
    
    st.title("⚙️ Ayarlar")
    
    st.subheader("🔄 Manuel Sıfırlama")
    st.caption("Dikkat: Bu işlemler geri alınamaz!")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🌅 Günlük Sıfırlama", use_container_width=True):
            count = reset_daily_tasks()
            st.success(f"✅ {count} günlük görev sıfırlandı!")
    
    with col2:
        if st.button("📆 Haftalık Sıfırlama", use_container_width=True):
            count = reset_weekly_tasks()
            st.success(f"✅ {count} haftalık görev sıfırlandı!")
    
    st.write("---")
    
    st.subheader("📖 Bot Komutları")
    st.markdown("""
    | Komut | Açıklama |
    |-------|----------|
    | `!baslat` | Bildirimleri başlat |
    | `!durdur` | Bildirimleri durdur |
    | `!durum` | Tüm görevlerin durumu |
    | `!kontrol` | Hazır görevleri kontrol et |
    | `!gunluk` | Günlük görevler |
    | `!haftalik` | Haftalık görevler |
    | `!instancelar` | Instance durumları |
    | `!ayarlar` | Bot ayarları |
    | `!yardim` | Yardım menüsü |
    """)
    
    st.write("---")
    
    st.subheader("ℹ️ Sistem Bilgisi")
    st.info(
        "**Veritabanı:** PostgreSQL\n"
        "**Kontrol Sıklığı:** Her 1 dakika\n"
        "**Otomatik Yenileme:** 60 dakika\n"
        "**Sıfırlama Saati:** 04:00"
    )


if __name__ == "__main__":
    main()

