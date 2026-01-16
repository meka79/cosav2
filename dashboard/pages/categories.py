"""
Kategori Yönetimi Sayfası - PostgreSQL destekli.
"""

import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.database.operations import (
    get_all_categories,
    get_tasks_by_category,
    add_category,
    update_category,
    delete_category,
    set_category_active
)


def show():
    """Kategori yönetimi sayfası."""
    
    st.title("📁 Kategori Yönetimi")
    
    tab1, tab2 = st.tabs(["📋 Kategorileri Gör", "➕ Yeni Kategori Ekle"])
    
    with tab1:
        show_categories_list()
    
    with tab2:
        show_add_category_form()


def show_categories_list():
    """Tüm kategorileri listele."""
    
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🔄 Yenile", key="refresh_cats"):
            st.rerun()
    with col2:
        show_inactive = st.checkbox("Pasif kategorileri göster", key="show_inactive")
    
    categories = get_all_categories(include_inactive=show_inactive)
    
    if not categories:
        st.info("Kategori yok. 'Yeni Kategori Ekle' sekmesinden ekleyebilirsin.")
        return
    
    st.write("---")
    
    icons = {'daily': '🌅', 'weekly': '📆', 'cooldown': '⏱️', 'instance': '🏰'}
    type_names = {'daily': 'Günlük', 'weekly': 'Haftalık', 'cooldown': 'Bekleme Süreli', 'instance': 'Instance'}
    
    for cat in categories:
        icon = icons.get(cat['reset_type'], '📁')
        is_active = cat.get('is_active', True)
        prefix = "" if is_active else "🚫 "
        
        with st.expander(f"{prefix}{icon} **{cat['name']}**"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**Açıklama:** {cat.get('description') or '-'}")
                st.write(f"**Sıfırlama Tipi:** {type_names.get(cat['reset_type'], cat['reset_type'])}")
                st.write(f"**Durum:** {'✅ Aktif' if is_active else '🚫 Pasif'}")
                
                pre_mins = cat.get('pre_notify_minutes', 0)
                resource = cat.get('show_resource_reminder', False)
                
                if pre_mins > 0:
                    st.write(f"**Ön Bildirim:** {pre_mins} dakika önce")
                    if resource:
                        st.write("**Kaynak Hatırlatması:** ✅ Açık")
                else:
                    st.caption("Ön bildirim: Kapalı")
                
                tasks = get_tasks_by_category(cat['id'])
                st.write(f"**Görev Sayısı:** {len(tasks)}")
                
                if cat.get('discord_channel_id'):
                    st.caption(f"Kanal: `{cat['discord_channel_id']}`")
            
            with col2:
                new_active = st.toggle("Aktif", value=is_active, key=f"active_{cat['id']}")
                if new_active != is_active:
                    set_category_active(cat['id'], new_active)
                    st.rerun()
                
                if st.button("✏️ Düzenle", key=f"edit_cat_{cat['id']}"):
                    st.session_state['editing_category_id'] = cat['id']
                    st.rerun()
                
                delete_key = f"del_cat_{cat['id']}"
                if delete_key not in st.session_state:
                    st.session_state[delete_key] = False
                
                if not st.session_state[delete_key]:
                    if st.button("🗑️", key=f"del_btn_{cat['id']}"):
                        st.session_state[delete_key] = True
                        st.rerun()
                else:
                    st.warning("Emin misin?")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅", key=f"yes_{cat['id']}"):
                            delete_category(cat['id'])
                            st.session_state[delete_key] = False
                            st.rerun()
                    with c2:
                        if st.button("❌", key=f"no_{cat['id']}"):
                            st.session_state[delete_key] = False
                            st.rerun()
    
    if 'editing_category_id' in st.session_state and st.session_state['editing_category_id']:
        show_edit_category_form(st.session_state['editing_category_id'])


def show_add_category_form():
    """Yeni kategori ekleme formu."""
    
    st.subheader("➕ Yeni Kategori Ekle")
    
    name = st.text_input("📁 Kategori Adı", key="new_cat_name")
    description = st.text_area("📄 Açıklama", key="new_cat_desc", height=80)
    
    reset_types = ['daily', 'weekly', 'cooldown', 'instance']
    labels = {
        'daily': '🌅 Günlük (04:00 sıfırlama)',
        'weekly': '📆 Haftalık (Pazartesi 04:00)',
        'cooldown': '⏱️ Bekleme Süreli (tamamlandıktan sonra)',
        'instance': '🏰 Instance (açık kalma + bekleme)'
    }
    
    reset_type = st.selectbox("⚙️ Sıfırlama Tipi", reset_types, format_func=lambda x: labels.get(x, x), key="new_cat_type")
    
    st.write("---")
    
    if st.button("✅ Kategori Ekle", type="primary", key="add_cat_btn"):
        if not name or not name.strip():
            st.error("Kategori adı gerekli!")
        else:
            try:
                new_id = add_category(name.strip(), description.strip() if description else "", reset_type)
                st.success(f"✅ Kategori eklendi! (ID: {new_id})")
                st.balloons()
            except Exception as e:
                if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                    st.error("Bu kategori zaten mevcut!")
                else:
                    st.error(str(e))


def show_edit_category_form(category_id: int):
    """Kategori düzenleme formu."""
    
    categories = get_all_categories(include_inactive=True)
    cat = next((c for c in categories if c['id'] == category_id), None)
    
    if not cat:
        st.error("Bulunamadı!")
        st.session_state['editing_category_id'] = None
        return
    
    st.write("---")
    st.subheader(f"✏️ Düzenleniyor: {cat['name']}")
    
    edit_name = st.text_input("📁 Kategori Adı", value=cat['name'], key="edit_cat_name")
    edit_desc = st.text_area("📄 Açıklama", value=cat.get('description', '') or '', key="edit_cat_desc", height=80)
    
    reset_types = ['daily', 'weekly', 'cooldown', 'instance']
    labels = {'daily': '🌅 Günlük', 'weekly': '📆 Haftalık', 'cooldown': '⏱️ Bekleme Süreli', 'instance': '🏰 Instance'}
    
    current_idx = reset_types.index(cat['reset_type']) if cat['reset_type'] in reset_types else 0
    edit_type = st.selectbox("⚙️ Sıfırlama Tipi", reset_types, index=current_idx, format_func=lambda x: labels.get(x, x), key="edit_cat_type")
    
    edit_active = st.checkbox("✅ Aktif", value=cat.get('is_active', True), key="edit_cat_active")
    
    st.write("---")
    st.subheader("⏳ Ön Bildirim Ayarları")
    
    st.caption("Görevler hazır olmadan X dakika önce bildirim al")
    
    pre_mins = st.number_input(
        "Ön bildirim (dakika)",
        min_value=0,
        max_value=60,
        value=cat.get('pre_notify_minutes', 0),
        help="0 = kapalı. Örn: 5 = görev hazır olmadan 5 dk önce bildir",
        key="edit_cat_pre_notify"
    )
    
    show_resource = st.checkbox(
        "Kaynak hatırlatması göster (Kaynağını hazırlamayı unutma!)",
        value=cat.get('show_resource_reminder', False),
        key="edit_cat_resource"
    )
    
    st.write("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 Kaydet", type="primary", key="save_cat"):
            if not edit_name or not edit_name.strip():
                st.error("Kategori adı gerekli!")
            else:
                try:
                    update_category(
                        category_id=category_id,
                        name=edit_name.strip(),
                        description=edit_desc.strip() if edit_desc else "",
                        reset_type=edit_type,
                        is_active=edit_active,
                        pre_notify_minutes=pre_mins,
                        show_resource_reminder=show_resource
                    )
                    st.success("✅ Güncellendi!")
                    st.session_state['editing_category_id'] = None
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
    
    with col2:
        if st.button("❌ İptal", key="cancel_cat"):
            st.session_state['editing_category_id'] = None
            st.rerun()
