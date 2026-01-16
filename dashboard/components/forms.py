"""
Form Bileşenleri - Türkçe Lokalizasyon.
"""

import streamlit as st
from typing import Optional


def duration_input(label_prefix: str, key_prefix: str, default_minutes: int = 0) -> int:
    """
    Süre girişi - Gün/Saat/Dakika.
    Toplam dakika olarak döndürür.
    """
    
    # Varsayılan değerlerden hesapla
    days = default_minutes // (24 * 60)
    remaining = default_minutes % (24 * 60)
    hours = remaining // 60
    minutes = remaining % 60
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        d = st.number_input("Gün", min_value=0, max_value=30, value=days, key=f"{key_prefix}_days")
    with col2:
        h = st.number_input("Saat", min_value=0, max_value=23, value=hours, key=f"{key_prefix}_hours")
    with col3:
        m = st.number_input("Dakika", min_value=0, max_value=59, value=minutes, key=f"{key_prefix}_mins")
    
    total = (d * 24 * 60) + (h * 60) + m
    
    if total > 0:
        st.caption(f"Toplam: {format_duration_display(total)}")
    
    return total


def format_duration_display(minutes: int) -> str:
    """Dakikayı okunabilir formata çevir."""
    if minutes <= 0:
        return "-"
    
    days = minutes // (24 * 60)
    remaining = minutes % (24 * 60)
    hours = remaining // 60
    mins = remaining % 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}g")
    if hours > 0:
        parts.append(f"{hours}s")
    if mins > 0:
        parts.append(f"{mins}dk")
    
    return " ".join(parts) if parts else "-"
