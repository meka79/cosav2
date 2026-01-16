"""
Durum Sayfası - PostgreSQL destekli.
"""

import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.operations import get_all_tasks_with_status, get_all_categories
from src.utils.time_utils import format_duration


def show():
    """Durum sayfası."""
    
    st.title("📊 Görev Durumu")
    
    if st.button("🔄 Yenile", key="refresh_status"):
        st.rerun()
    
    tasks = get_all_tasks_with_status()
    
    if not tasks:
        st.info("Henüz görev eklenmemiş. 'Görevler' sekmesinden ekleyebilirsin!")
        return
    
    # Özet istatistikler
    show_summary(tasks)
    
    st.write("---")
    
    # Kategori bazlı görevler
    show_by_category(tasks)


def show_summary(tasks):
    """Özet istatistikler."""
    
    total = len(tasks)
    ready = sum(1 for t in tasks if t.get('is_available') or t.get('is_open'))
    completed = sum(1 for t in tasks if t.get('is_completed'))
    on_cooldown = total - ready - completed
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📋 Toplam", total)
    with col2:
        st.metric("🟢 Hazır", ready)
    with col3:
        st.metric("✅ Tamamlanan", completed)
    with col4:
        st.metric("🔴 Beklemede", on_cooldown)


def show_by_category(tasks):
    """Kategori bazlı görevler."""
    
    # Kategorilere göre grupla
    categories = {}
    for task in tasks:
        cat_name = task.get('category_name', 'Bilinmeyen')
        if cat_name not in categories:
            categories[cat_name] = []
        categories[cat_name].append(task)
    
    icons = {'daily': '🌅', 'weekly': '📆', 'cooldown': '⏱️', 'instance': '🏰'}
    
    for cat_name, cat_tasks in categories.items():
        reset_type = cat_tasks[0].get('reset_type', 'unknown') if cat_tasks else 'unknown'
        icon = icons.get(reset_type, '📁')
        
        ready_count = sum(1 for t in cat_tasks if t.get('is_available') or t.get('is_open'))
        
        header = f"{icon} {cat_name}"
        if ready_count > 0:
            header += f" 🔔 ({ready_count} hazır)"
        
        with st.expander(header, expanded=ready_count > 0):
            for task in cat_tasks:
                show_task_card(task)


def show_task_card(task):
    """Tek görev kartı."""
    
    emoji = task.get('status_emoji', '❓')
    name = task['name']
    message = task.get('status_message', '')
    reset_type = task.get('reset_type', 'unknown')
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.write(f"### {emoji}")
    
    with col2:
        st.write(f"**{name}**")
        st.caption(message)
        
        # Ekstra bilgi
        if reset_type in ['cooldown', 'instance']:
            cd = task.get('cooldown_minutes', 0)
            if cd > 0:
                st.caption(f"⏱️ Bekleme: {format_duration(cd)}")
        
        if reset_type == 'instance':
            active = task.get('active_duration_minutes', 0)
            if active > 0:
                st.caption(f"🔓 Açık kalma: {format_duration(active)}")
    
    st.write("")
