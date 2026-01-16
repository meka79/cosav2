import streamlit as st
from src.database.operations import (
    get_all_categories, 
    add_category, 
    update_category, 
    delete_category
)

def show():
    """Kategori yönetimi sayfasını göster."""
    st.title("📂 Kategori Yönetimi")
    
    # --- YENİ KATEGORİ EKLE ---
    with st.expander("➕ Yeni Kategori Ekle", expanded=False):
        with st.form("add_cat_form"):
            new_name = st.text_input("Kategori Adı", placeholder="Örn: Zindanlar")
            new_desc = st.text_area("Açıklama", placeholder="Kısa açıklama...")
            
            # Reset Tipi Seçimi
            reset_options = {
                "daily": "Günlük (Her sabah 04:00)",
                "weekly": "Haftalık (Pazartesi 04:00)",
                "cooldown": "Bekleme Süreli (Örn: 3 saat)",
                "instance": "Giriş/Çıkışlı (Instance)"
            }
            new_type_key = st.selectbox(
                "Sıfırlama Tipi", 
                options=list(reset_options.keys()),
                format_func=lambda x: reset_options[x]
            )
            
            submitted = st.form_submit_button("Ekle")
            if submitted:
                if new_name:
                    add_category(new_name, new_desc, new_type_key)
                    st.success(f"✅ {new_name} eklendi!")
                    st.rerun()
                else:
                    st.error("⚠️ İsim boş olamaz.")

    st.divider()

    # --- MEVCUT KATEGORİLERİ LİSTELE ---
    categories = get_all_categories(include_inactive=True)
    
    if not categories:
        st.info("Henüz kategori yok.")
        return

    for cat in categories:
        # Her kategori için bir kutu (container)
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            
            # Başlık ve Durum
            status_icon = "🟢" if cat['is_active'] else "🔴"
            c1.subheader(f"{status_icon} {cat['name']}")
            c1.caption(f"Tip: {cat['reset_type']} | {cat['description']}")
            
            # Gelişmiş Bilgiler (Hatırlatma vb.)
            info_text = []
            if cat.get('pre_notify_minutes', 0) > 0:
                info_text.append(f"⏰ {cat['pre_notify_minutes']}dk önce bildirim")
            if cat.get('show_resource_reminder'):
                info_text.append("🎒 Kaynak uyarısı aktif")
            
            if info_text:
                c1.info(" | ".join(info_text))
            
            # Düzenleme Modu (Checkbox ile açılır)
            is_editing = c2.checkbox("Düzenle", key=f"edit_mode_{cat['id']}")
            
            if is_editing:
                with st.form(f"edit_form_{cat['id']}"):
                    st.write(f"**{cat['name']} Düzenleniyor**")
                    
                    edit_name = st.text_input("Ad", value=cat['name'])
                    edit_desc = st.text_area("Açıklama", value=cat['description'])
                    edit_type = st.selectbox(
                        "Tip", 
                        options=list(reset_options.keys()),
                        index=list(reset_options.keys()).index(cat['reset_type']),
                        format_func=lambda x: reset_options[x],
                        key=f"type_select_{cat['id']}"
                    )
                    
                    # --- YENİ EKLENEN ÖZELLİKLER ---
                    st.markdown("---")
                    st.markdown("##### 🔔 Bildirim Ayarları")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        edit_pre_notify = st.number_input(
                            "Erken Bildirim (Dakika)",
                            min_value=0,
                            max_value=1440,
                            value=int(cat.get('pre_notify_minutes', 0)),
                            help="Süre dolmadan kaç dakika önce 'Hazırlan' mesajı atılsın? (0 = Kapalı)"
                        )
                    with col_b:
                        edit_resource = st.checkbox(
                            "🎒 Kaynak Hatırlatıcı?",
                            value=bool(cat.get('show_resource_reminder', False)),
                            help="Bildirimde 'Kaynakları hazırlamayı unutma' yazsın mı?"
                        )
                    st.markdown("---")
                    # -------------------------------
                    
                    edit_active = st.checkbox("Aktif", value=cat['is_active'])
                    
                    # Kaydet ve Sil Butonları
                    col1, col2 = st.columns([1, 1])
                    if col1.form_submit_button("💾 Kaydet"):
                        update_category(
                            cat['id'], 
                            edit_name, 
                            edit_desc, 
                            edit_type, 
                            edit_active,
                            pre_notify_minutes=edit_pre_notify,
                            show_resource_reminder=edit_resource
                        )
                        st.success("Güncellendi!")
                        st.rerun()
                    
                    if col2.form_submit_button("🗑️ Sil", type="primary"):
                        delete_category(cat['id'])
                        st.warning("Silindi!")
                        st.rerun()
