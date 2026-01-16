"""
Scheduler - PostgreSQL destekli.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

import discord
from discord.ext import commands

from src.database.operations import (
    get_tasks_grouped_by_category,
    get_tasks_needing_pre_notification,
    get_stale_notifications,
    get_all_categories,
    get_task_with_status,
    get_task_by_id,
    reset_daily_tasks,
    reset_weekly_tasks,
    mark_pre_notified,
    update_notification_sent
)
from src.database.models import get_setting, is_bot_active
from src.utils.time_utils import DAILY_RESET_HOUR, DAILY_RESET_MINUTE, WEEKLY_RESET_DAY


scheduler: Optional[AsyncIOScheduler] = None
MESSAGE_DELAY = 1.0
AUTO_REFRESH_MINUTES = 60


def setup_scheduler(bot: commands.Bot, fallback_channel: Optional[discord.TextChannel]) -> None:
    """Zamanlayıcıyı kur."""
    global scheduler
    
    if scheduler is not None:
        try:
            scheduler.shutdown(wait=False)
        except:
            pass
    
    scheduler = AsyncIOScheduler()
    scheduler.bot = bot
    scheduler.fallback_channel = fallback_channel
    
    # Ana kontrol: Her 1 dakika
    scheduler.add_job(
        main_check_cycle,
        IntervalTrigger(minutes=1),
        id='main_cycle',
        name='Ana Kontrol (1dk)',
        replace_existing=True
    )
    
    # Günlük reset 04:00
    scheduler.add_job(
        daily_reset_job,
        CronTrigger(hour=DAILY_RESET_HOUR, minute=DAILY_RESET_MINUTE),
        id='daily_reset',
        name='Günlük Reset',
        replace_existing=True
    )
    
    # Haftalık reset Pazartesi 04:00
    scheduler.add_job(
        weekly_reset_job,
        CronTrigger(day_of_week=WEEKLY_RESET_DAY, hour=DAILY_RESET_HOUR, minute=DAILY_RESET_MINUTE),
        id='weekly_reset',
        name='Haftalık Reset',
        replace_existing=True
    )
    
    # Haftalık hatırlatmalar
    scheduler.add_job(
        weekly_reminder_job,
        CronTrigger(day_of_week='wed,fri,sun', hour=20, minute=0),
        id='weekly_reminder',
        name='Haftalık Hatırlatma',
        replace_existing=True
    )
    
    # Günlük hatırlatma
    scheduler.add_job(
        daily_reminder_job,
        CronTrigger(hour=22, minute=0),
        id='daily_reminder',
        name='Günlük Hatırlatma',
        replace_existing=True
    )
    
    scheduler.start()
    print("📅 Zamanlayıcı başlatıldı:")
    print("   ⚡ Ana döngü: 1 dakika")
    print("   ⏳ Ön bildirim: aktif")
    print("   🔄 Otomatik yenileme: 60 dakika")


async def get_channel_for_category(category_name: str) -> Optional[discord.TextChannel]:
    """Kategori için Discord kanalı al."""
    global scheduler
    
    if not scheduler or not scheduler.bot.guilds:
        return scheduler.fallback_channel if scheduler else None
    
    guild = scheduler.bot.guilds[0]
    
    for cat in get_all_categories():
        if cat['name'] == category_name and cat.get('discord_channel_id'):
            try:
                ch = guild.get_channel(int(cat['discord_channel_id']))
                if ch:
                    return ch
            except:
                pass
    
    return scheduler.fallback_channel if scheduler else None


async def main_check_cycle() -> None:
    """Ana 1-dakikalık döngü."""
    global scheduler
    
    if not scheduler:
        return
    
    if not is_bot_active():
        return
    
    # 1. Ön bildirimler
    await send_pre_notifications()
    
    # 2. Hazır görev bildirimleri
    await send_available_notifications()
    
    # 3. Eski bildirimleri yenile
    await refresh_stale_messages()


async def send_pre_notifications() -> None:
    """Ön bildirimler gönder."""
    global scheduler
    
    tasks = get_tasks_needing_pre_notification()
    
    if not tasks:
        return
    
    from src.bot.notifications import send_pre_notification
    
    for task in tasks:
        cat_name = task.get('category_name', 'Bilinmeyen')
        channel = await get_channel_for_category(cat_name)
        
        if not channel:
            continue
        
        try:
            await send_pre_notification(channel, task)
            mark_pre_notified(task['id'])
            await asyncio.sleep(MESSAGE_DELAY)
        except Exception as e:
            print(f"Ön bildirim hatası: {e}")


async def send_available_notifications() -> None:
    """Hazır görev bildirimleri gönder."""
    global scheduler
    
    grouped = get_tasks_grouped_by_category()
    
    if not grouped:
        return
    
    from src.bot.notifications import send_lite_notification
    
    total = 0
    
    for cat_name, tasks in grouped.items():
        channel = await get_channel_for_category(cat_name)
        if not channel:
            continue
        
        for task in tasks:
            try:
                await send_lite_notification(channel, task)
                total += 1
                await asyncio.sleep(MESSAGE_DELAY)
            except Exception as e:
                print(f"Bildirim hatası: {e}")
                await asyncio.sleep(2)
    
    if total > 0:
        print(f"⚡ {total} bildirim gönderildi")


async def refresh_stale_messages() -> None:
    """Eski mesajları sil ve yeniden bildir."""
    global scheduler
    
    if not scheduler or not scheduler.bot.guilds:
        return
    
    guild = scheduler.bot.guilds[0]
    
    try:
        refresh_mins = int(get_setting('auto_refresh_minutes', '60'))
    except:
        refresh_mins = 60
    
    stale_tasks = get_stale_notifications(refresh_mins)
    
    if not stale_tasks:
        return
    
    from src.bot.notifications import send_lite_notification
    
    for task in stale_tasks:
        fresh = get_task_by_id(task['id'])
        if not fresh:
            continue
        
        fresh_status = get_task_with_status(fresh)
        
        if not (fresh_status.get('is_available') or fresh_status.get('is_open')):
            continue
        
        channel_id = task.get('discord_channel_id')
        channel = None
        
        if channel_id:
            try:
                channel = guild.get_channel(int(channel_id))
            except:
                pass
        
        if not channel:
            channel = await get_channel_for_category(task.get('category_name', ''))
        
        if not channel:
            continue
        
        old_msg_id = task.get('notification_message_id')
        if old_msg_id:
            try:
                old_msg = await channel.fetch_message(int(old_msg_id))
                await old_msg.delete()
            except:
                pass
        
        try:
            await send_lite_notification(channel, fresh_status)
            print(f"🔄 Yenilendi: {task['name']}")
            await asyncio.sleep(MESSAGE_DELAY)
        except Exception as e:
            print(f"Yenileme hatası: {e}")


async def daily_reset_job() -> None:
    """Günlük reset."""
    if not is_bot_active():
        reset_daily_tasks()
        return
    
    count = reset_daily_tasks()
    print(f"🌅 Günlük reset: {count}")
    
    channel = await get_channel_for_category('Daily Quests')
    if not channel and scheduler:
        channel = scheduler.fallback_channel
    
    if channel:
        await channel.send(f"🌅 **Günlük Reset** - {count} görev sıfırlandı!")


async def weekly_reset_job() -> None:
    """Haftalık reset."""
    if not is_bot_active():
        reset_weekly_tasks()
        return
    
    count = reset_weekly_tasks()
    print(f"📆 Haftalık reset: {count}")
    
    channel = await get_channel_for_category('Weekly Quests')
    if not channel and scheduler:
        channel = scheduler.fallback_channel
    
    if channel:
        await channel.send(f"📆 **Haftalık Reset** - {count} görev sıfırlandı!")


async def weekly_reminder_job() -> None:
    """Haftalık hatırlatma."""
    if not is_bot_active():
        return
    
    channel = await get_channel_for_category('Weekly Quests')
    if not channel and scheduler:
        channel = scheduler.fallback_channel
    
    if channel:
        from src.bot.notifications import send_weekly_reminder
        await send_weekly_reminder(channel)


async def daily_reminder_job() -> None:
    """Günlük hatırlatma."""
    if not is_bot_active():
        return
    
    channel = await get_channel_for_category('Daily Quests')
    if not channel and scheduler:
        channel = scheduler.fallback_channel
    
    if channel:
        from src.bot.notifications import send_daily_reminder
        await send_daily_reminder(channel)


def get_scheduler() -> Optional[AsyncIOScheduler]:
    return scheduler
