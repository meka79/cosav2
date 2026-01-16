"""
Reaksiyon işleyici - Türkçe mesajlar.
✅ Yaptım - Bekleme süresini başlatır
❌ Geç - Bildirimi geçer, tekrar hatırlatmaz
⏰ Hatırlat - Mesajı siler, 10 dk sonra tekrar bildirir
"""

import asyncio
import discord
from discord.ext import commands
from datetime import timedelta

from src.database.operations import (
    get_task_by_message_id,
    get_task_by_id,
    mark_task_completed,
    mark_instance_entered,
    get_task_with_status,
    update_task_last_status
)
from src.scheduler.timers import TaskState
from src.utils.time_utils import format_duration, now


EMOJI_COMPLETE = "✅"
EMOJI_SKIP = "❌"
EMOJI_SNOOZE = "⏰"

SNOOZE_MINUTES = 10


async def handle_reaction_add(
    reaction: discord.Reaction,
    user: discord.User,
    bot: commands.Bot
) -> None:
    """Bildirim mesajlarındaki reaksiyonları işle."""
    emoji = str(reaction.emoji)
    
    if emoji not in [EMOJI_COMPLETE, EMOJI_SKIP, EMOJI_SNOOZE]:
        return
    
    message_id = str(reaction.message.id)
    task = get_task_by_message_id(message_id)
    
    if not task:
        return
    
    if emoji == EMOJI_COMPLETE:
        await handle_complete(reaction, task, user)
    elif emoji == EMOJI_SKIP:
        await handle_skip(reaction, task, user)
    elif emoji == EMOJI_SNOOZE:
        await handle_snooze(reaction, task, user, bot)


async def handle_complete(
    reaction: discord.Reaction,
    task: dict,
    user: discord.User
) -> None:
    """
    ✅ Yaptım - Bekleme süresini başlatır.
    """
    name = task['name']
    reset_type = task['reset_type']
    current = now()
    
    if reset_type == 'instance':
        mark_instance_entered(task['id'])
        
        active = task.get('active_duration_minutes', 0)
        cd = task.get('cooldown_minutes', 0)
        
        close_time = current + timedelta(minutes=active)
        next_time = close_time + timedelta(minutes=cd)
        
        response = (
            f"🏰 **{name}** girildi!\n"
            f"🔓 Kapanış: **{close_time.strftime('%H:%M')}**\n"
            f"⏰ Sonraki giriş: **{next_time.strftime('%d/%m %H:%M')}**"
        )
    else:
        mark_task_completed(task['id'])
        
        if reset_type == 'daily':
            from src.utils.time_utils import get_next_daily_reset
            next_reset = get_next_daily_reset()
            response = f"✅ **{name}** tamamlandı!\n🔄 Reset: **{next_reset.strftime('%d/%m %H:%M')}**"
        
        elif reset_type == 'weekly':
            from src.utils.time_utils import get_next_weekly_reset
            next_reset = get_next_weekly_reset()
            response = f"✅ **{name}** tamamlandı!\n🔄 Reset: **{next_reset.strftime('%d/%m %H:%M')}**"
        
        else:
            cd = task.get('cooldown_minutes', 0)
            next_time = current + timedelta(minutes=cd)
            response = (
                f"✅ **{name}** tamamlandı!\n"
                f"⏱️ Bekleme: **{format_duration(cd)}**\n"
                f"⏰ Tekrar hazır: **{next_time.strftime('%d/%m %H:%M')}**"
            )
    
    await reaction.message.channel.send(response)
    
    try:
        embed = discord.Embed(
            description=f"✅ ~~{name}~~ - Tamam",
            color=0x2ecc71
        )
        await reaction.message.edit(embed=embed)
        await reaction.message.clear_reactions()
    except:
        pass


async def handle_skip(
    reaction: discord.Reaction,
    task: dict,
    user: discord.User
) -> None:
    """
    ❌ Geç - Bildirimi geçer.
    """
    name = task['name']
    
    update_task_last_status(task['id'], 'skipped')
    
    try:
        embed = discord.Embed(
            description=f"⏭️ ~~{name}~~ - Geçildi",
            color=0x95a5a6
        )
        await reaction.message.edit(embed=embed)
        await reaction.message.clear_reactions()
    except:
        pass


async def handle_snooze(
    reaction: discord.Reaction,
    task: dict,
    user: discord.User,
    bot: commands.Bot
) -> None:
    """
    ⏰ Hatırlat - Mesajı siler, 10 dk sonra tekrar bildirir.
    """
    name = task['name']
    channel = reaction.message.channel
    
    try:
        await reaction.message.delete()
    except:
        pass
    
    confirm = await channel.send(f"⏰ **{name}** için {SNOOZE_MINUTES} dk sonra hatırlatılacak.")
    
    async def snooze_callback():
        await asyncio.sleep(SNOOZE_MINUTES * 60)
        
        fresh_task = get_task_by_id(task['id'])
        if fresh_task:
            fresh_with_status = get_task_with_status(fresh_task)
            
            if fresh_with_status.get('is_available') or fresh_with_status.get('is_open'):
                from src.bot.notifications import send_lite_notification
                await send_lite_notification(channel, fresh_with_status)
        
        try:
            await confirm.delete()
        except:
            pass
    
    asyncio.create_task(snooze_callback())
