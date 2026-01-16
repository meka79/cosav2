"""
Görev Yönetimi Sayfası - PostgreSQL destekli.
"""

import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.operations import (
    get_all_tasks_with_status,
    get_all_categories,
    get_task_by_id,
    add_task,
    update_task,
    hard_delete_task
)
from dashboard.components.forms import duration_input, format_duration_display


def show():
    """Görev yönetimi sayfasını göster."""
    
    st.title("📋 Görev Yönetimi")
    
    tab1, tab2 = st.tabs(["📝 Görevleri Gör & Düzenle", "➕ Yeni Görev Ekle"])
    
    with tab1:
        show_tasks_list()
    
    with tab2:
        show_add_task_form()


def show_tasks_list():
    """Tüm görevleri listele."""
    
    if st.button("🔄 Yenile", key="refresh_tasks"):
        st.rerun()
    
    tasks = get_all_tasks_with_status()
    categories = get_all_categories(include_inactive=True)
    
    if not tasks:
        st.info("Henüz görev yok. 'Yeni Görev Ekle' sekmesinden ekleyebilirsin!")
        return
    
    category_names = ["Tüm Kategoriler"] + [c['name'] for c in categories]
    selected_filter = st.selectbox("Kategoriye Göre Filtrele", category_names, key="task_filter")
    
    if selected_filter != "Tüm Kategoriler":
        tasks = [t for t in tasks if t.get('category_name') == selected_filter]
    
    st.write("---")
    
    for task in tasks:
        with st.expander(
            f"{task.get('status_emoji', '📋')} **{task['name']}** - {task.get('category_name', 'Bilinmeyen')}"
        ):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**Açıklama:** {task.get('description') or 'Açıklama yok'}")
                st.write(f"**Durum:** {task.get('status_message', 'Bilinmeyen')}")
                st.write(f"**Sıfırlama Tipi:** {task.get('reset_type', 'Bilinmeyen')}")
                
                if task.get('reset_type') in ['cooldown', 'instance']:
                    st.write(f"**Bekleme Süresi:** {format_duration_display(task.get('cooldown_minutes', 0))}")
                
                if task.get('reset_type') == 'instance':
                    st.write(f"**Açık Kalma Süresi:** {format_duration_display(task.get('active_duration_minutes', 0))}")
            
            with col2:
                if st.button("✏️ Düzenle", key=f"edit_btn_{task['id']}"):
                    st.session_state['editing_task_id'] = task['id']
                    st.rerun()
                
                delete_key = f"confirm_delete_{task['id']}"
                if delete_key not in st.session_state:
                    st.session_state[delete_key] = False
                
                if not st.session_state[delete_key]:
                    if st.button("🗑️ Sil", key=f"delete_btn_{task['id']}"):
                        st.session_state[delete_key] = True
                        st.rerun()
                else:
                    st.warning("Emin misin?")
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("✅ Evet", key=f"yes_{task['id']}"):
                            hard_delete_task(task['id'])
                            st.session_state[delete_key] = False
                            st.success(f"{task['name']} silindi")
                            st.rerun()
                    with col_no:
                        if st.button("❌ Hayır", key=f"no_{task['id']}"):
                            st.session_state[delete_key] = False
                            st.rerun()
    
    if 'editing_task_id' in st.session_state and st.session_state['editing_task_id']:
        show_edit_task_form(st.session_state['editing_task_id'], categories)


def show_add_task_form():
    """Yeni görev ekleme formu."""
    
    st.subheader("➕ Yeni Görev Ekle")
    
    categories = get_all_categories()
    
    if not categories:
        st.error("Kategori yok. Önce kategori ekle!")
        return
    
    category_names = [c['name'] for c in categories]
    category_map = {c['name']: c for c in categories}
    
    selected_category_name = st.selectbox(
        "📁 Kategori Seç",
        category_names,
        key="add_task_category_select"
    )
    
    selected_category = category_map[selected_category_name]
    reset_type = selected_category['reset_type']
    
    reset_info = {
        'daily': ("🌅 Günlük Sıfırlama", "Her gün 04:00'da sıfırlanır"),
        'weekly': ("📆 Haftalık Sıfırlama", "Her Pazartesi 04:00'da sıfırlanır"),
        'cooldown': ("⏱️ Bekleme Süreli", "Aşağıdan bekleme süresini gir"),
        'instance': ("🏰 Instance", "Açık kalma ve bekleme süresini gir")
    }
    
    info_title, info_desc = reset_info.get(reset_type, ("Bilinmeyen", ""))
    st.info(f"**{info_title}**: {info_desc}")
    
    st.write("---")
    
    task_name = st.text_input(
        "📝 Görev Adı",
        placeholder="örn: Dragon Altar",
        key="new_task_name"
    )
    
    task_description = st.text_area(
        "📄 Açıklama (opsiyonel)",
        placeholder="Kısa açıklama",
        key="new_task_description",
        height=80
    )
    
    cooldown_minutes = 0
    active_duration_minutes = 0
    
    if reset_type == 'cooldown':
        st.write("---")
        st.subheader("⏱️ Bekleme Süresi")
        cooldown_minutes = duration_input("cooldown", "new_cd")
    
    elif reset_type == 'instance':
        st.write("---")
        st.subheader("🔓 Açık Kalma Süresi")
        st.caption("Instance ne kadar süre açık kalıyor")
        active_duration_minutes = duration_input("active", "new_active")
        
        st.write("---")
        st.subheader("⏱️ Bekleme Süresi")
        st.caption("Instance kapandıktan sonra bekleme süresi")
        cooldown_minutes = duration_input("cooldown", "new_cd")
    
    st.write("---")
    
    if st.button("✅ Görev Ekle", use_container_width=True, type="primary", key="add_task_submit"):
        if not task_name or not task_name.strip():
            st.error("⚠️ Görev adı gerekli!")
        else:
            try:
                new_id = add_task(
                    category_id=selected_category['id'],
                    name=task_name.strip(),
                    description=task_description.strip() if task_description else "",
                    cooldown_minutes=cooldown_minutes,
                    active_duration_minutes=active_duration_minutes
                )
                st.success(f"✅ '{task_name}' eklendi! (ID: {new_id})")
                st.balloons()
                
            except Exception as e:
                if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                    st.error(f"⚠️ '{task_name}' zaten mevcut!")
                else:
                    st.error(f"Hata: {e}")


def show_edit_task_form(task_id: int, categories: list):
    """Görev düzenleme formu."""
    
    task = get_task_by_id(task_id)
    
    if not task:
        st.error("Görev bulunamadı!")
        st.session_state['editing_task_id'] = None
        return
    
    st.write("---")
    st.subheader(f"✏️ Düzenleniyor: {task['name']}")
    
    st.info(f"**Kategori:** {task.get('category_name', 'Bilinmeyen')} ({task.get('reset_type', 'bilinmeyen')})")
    
    reset_type = task.get('reset_type', 'daily')
    
    edit_name = st.text_input(
        "📝 Görev Adı",
        value=task['name'],
        key="edit_name_input"
    )
    
    edit_description = st.text_area(
        "📄 Açıklama",
        value=task.get('description', '') or '',
        key="edit_desc_input",
        height=80
    )
    
    cooldown_minutes = task.get('cooldown_minutes', 0)
    active_duration_minutes = task.get('active_duration_minutes', 0)
    
    if reset_type == 'cooldown':
        st.write("---")
        st.subheader("⏱️ Bekleme Süresi")
        cooldown_minutes = duration_input(
            "cooldown", 
            "edit_cd",
            default_minutes=task.get('cooldown_minutes', 0)
        )
    
    elif reset_type == 'instance':
        st.write("---")
        st.subheader("🔓 Açık Kalma Süresi")
        active_duration_minutes = duration_input(
            "active",
            "edit_active",
            default_minutes=task.get('active_duration_minutes', 0)
        )
        
        st.write("---")
        st.subheader("⏱️ Bekleme Süresi")
        cooldown_minutes = duration_input(
            "cooldown",
            "edit_cd",
            default_minutes=task.get('cooldown_minutes', 0)
        )
    
    st.write("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 Kaydet", use_container_width=True, type="primary", key="save_edit"):
            if not edit_name or not edit_name.strip():
                st.error("Görev adı gerekli!")
            else:
                try:
                    update_task(
                        task_id=task_id,
                        name=edit_name.strip(),
                        description=edit_description.strip() if edit_description else "",
                        cooldown_minutes=cooldown_minutes,
                        active_duration_minutes=active_duration_minutes
                    )
                    st.success(f"✅ Güncellendi!")
                    st.session_state['editing_task_id'] = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Hata: {e}")
    
    with col2:
        if st.button("❌ İptal", use_container_width=True, key="cancel_edit"):
            st.session_state['editing_task_id'] = None
            st.rerun()
