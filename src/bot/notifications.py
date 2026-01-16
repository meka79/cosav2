"""
Bildirim sistemi - Türkçe lokalizasyon.
Lite embed formatı korunmuş, oyuncu dostu Türkçe mesajlar.
"""

import discord
from typing import Optional, Dict, List

from src.database.operations import (
    get_all_tasks_with_status,
    update_notification_sent
)
from src.utils.time_utils import format_duration


EMOJI_COMPLETE = "✅"
EMOJI_SKIP = "❌"
EMOJI_SNOOZE = "⏰"


async def send_lite_notification(
    channel: discord.TextChannel,
    task: Dict
) -> Optional[discord.Message]:
    """Lite embed bildirimi gönder - 3 butonlu."""
    reset_type = task['reset_type']
    name = task['name']
    
    colors = {
        'daily': 0x3498db,
        'weekly': 0x9b59b6,
        'cooldown': 0xe67e22,
        'instance': 0xf1c40f,
    }
    
    embed = discord.Embed(color=colors.get(reset_type, 0x95a5a6))
    
    if reset_type == 'instance':
        embed.description = f"🏰 **{name}** girilebilir durumda!"
    elif reset_type == 'daily':
        embed.description = f"📋 **{name}** bugün yapılmadı!"
    elif reset_type == 'weekly':
        embed.description = f"📋 **{name}** bu hafta yapılmadı!"
    else:
        embed.description = f"🔔 **{name}** hazır!"
    
    cd = task.get('cooldown_minutes', 0)
    if cd > 0:
        embed.description += f" | Bekleme: **{format_duration(cd)}**"
    
    if reset_type == 'instance':
        active = task.get('active_duration_minutes', 0)
        if active > 0:
            embed.description += f" | Açık kalma: **{format_duration(active)}**"
    
    embed.description += "\n\n✅ Yaptım | ❌ Geç | ⏰ Hatırlat"
    
    message = await channel.send(embed=embed)
    
    await message.add_reaction(EMOJI_COMPLETE)
    await message.add_reaction(EMOJI_SKIP)
    await message.add_reaction(EMOJI_SNOOZE)
    
    update_notification_sent(task['id'], str(message.id), 'notified')
    
    return message


async def send_pre_notification(
    channel: discord.TextChannel,
    task: Dict
) -> Optional[discord.Message]:
    """
    Ön bildirim - görev hazır olmadan X dakika önce.
    Amber/turuncu renk.
    """
    name = task['name']
    pre_mins = task.get('pre_notify_minutes', 5)
    show_reminder = task.get('show_resource_reminder', False)
    
    embed = discord.Embed(color=0xf39c12)
    
    embed.description = f"⏳ **{name}** {pre_mins} dakika sonra hazır olacak!"
    
    if show_reminder:
        embed.description += "\n\n*(Kaynağını hazırlamayı unutma!)*"
    
    message = await channel.send(embed=embed)
    
    return message


async def send_task_notification(channel: discord.TextChannel, task: Dict, **kwargs) -> Optional[discord.Message]:
    """Görev bildirimi gönder."""
    return await send_lite_notification(channel, task)


async def send_status_overview(channel: discord.TextChannel) -> None:
    """Genel durum özeti gönder."""
    tasks = get_all_tasks_with_status()
    
    if not tasks:
        await channel.send("📋 Henüz görev eklenmemiş.")
        return
    
    categories: Dict[str, List[Dict]] = {}
    for t in tasks:
        cat = t.get('category_name', 'Bilinmeyen')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(t)
    
    embed = discord.Embed(title="🐉 Görev Durumu", color=0x2c3e50)
    
    for cat_name, cat_tasks in categories.items():
        lines = []
        for t in cat_tasks:
            emoji = t.get('status_emoji', '❓')
            msg = t.get('status_message', '')
            if len(msg) > 25:
                msg = msg[:22] + "..."
            lines.append(f"{emoji} **{t['name']}** - {msg}")
        
        value = "\n".join(lines)
        if len(value) > 1024:
            value = value[:1020] + "..."
        
        embed.add_field(name=f"📁 {cat_name}", value=value, inline=False)
    
    await channel.send(embed=embed)


async def send_daily_reminder(channel: discord.TextChannel) -> None:
    """Günlük görev hatırlatması."""
    tasks = get_all_tasks_with_status()
    incomplete = [t for t in tasks if t['reset_type'] == 'daily' and not t.get('is_completed')]
    
    if not incomplete:
        return
    
    names = ", ".join([t['name'] for t in incomplete[:5]])
    extra = f" +{len(incomplete)-5} tane daha" if len(incomplete) > 5 else ""
    
    await channel.send(f"⏰ **Günlük görevler kaldı:** {names}{extra}")


async def send_weekly_reminder(channel: discord.TextChannel) -> None:
    """Haftalık görev hatırlatması."""
    from src.utils.time_utils import get_weekly_urgency_message
    
    tasks = get_all_tasks_with_status()
    incomplete = [t for t in tasks if t['reset_type'] == 'weekly' and not t.get('is_completed')]
    
    if not incomplete:
        return
    
    urgency = get_weekly_urgency_message()
    names = ", ".join([t['name'] for t in incomplete])
    
    await channel.send(f"📆 {urgency}\n**Kalan görevler:** {names}")


async def send_available_notification(channel: discord.TextChannel, task: Dict) -> None:
    """Hazır görev bildirimi."""
    await send_lite_notification(channel, task)
