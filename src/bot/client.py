"""
Discord Bot - PostgreSQL destekli, timezone-aware.
Görünmezlik modu (Invisible) eklendi.
"""

import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

from src.database.models import init_db, get_setting, set_setting, is_bot_active, set_bot_active
from src.database.operations import (
    get_all_categories,
    set_category_channel,
    get_all_tasks_with_status,
    get_tasks_by_category,
    get_task_with_status,
    get_category_by_channel_id
)
from src.bot.notifications import send_lite_notification, send_status_overview
from src.bot.reactions import handle_reaction_add
from src.scheduler.jobs import setup_scheduler
from src.utils.time_utils import format_duration

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "")
PARENT_CATEGORY_ID = os.getenv("DISCORD_PARENT_CATEGORY_ID", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")

MESSAGE_DELAY = 1.0

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

notification_channel = None
guild_ref = None


async def get_or_create_general_channel():
    """Genel kanal oluştur veya bul."""
    global guild_ref
    
    if CHANNEL_ID:
        ch = bot.get_channel(int(CHANNEL_ID))
        if ch:
            return ch
    
    parent_id = get_setting('discord_parent_category_id', PARENT_CATEGORY_ID)
    if not parent_id or not guild_ref:
        return None
    
    try:
        parent = guild_ref.get_channel(int(parent_id))
        if not parent:
            return None
        
        for ch in parent.channels:
            if ch.name in ['general-tasks', 'genel-gorevler']:
                return ch
        
        return await guild_ref.create_text_channel(name='genel-gorevler', category=parent)
    except:
        return None


@bot.event
async def on_ready():
    global notification_channel, guild_ref
    
    print("━" * 40)
    print("🐉 War of Dragons - Görev Takipçisi")
    print("🚀 SÜRÜM: 3.6 - OFFLINE MODLU")
    print("━" * 40)
    print(f"✅ Bot: {bot.user.name}")
    print(f"🗄️ Veritabanı: PostgreSQL")
    
    if DATABASE_URL:
        init_db()
    else:
        print("⚠️ DATABASE_URL ayarlanmamış!")
    
    if bot.guilds:
        guild_ref = bot.guilds[0]
        print(f"📍 Sunucu: {guild_ref.name}")
    
    if CHANNEL_ID:
        notification_channel = bot.get_channel(int(CHANNEL_ID))
    
    if not notification_channel:
        notification_channel = await get_or_create_general_channel()
    
    if notification_channel:
        print(f"📢 Kanal: #{notification_channel.name}")
    
    # Botun aktiflik durumunu kontrol et ve ona göre GÖRÜNÜM ayarla
    active = is_bot_active()
    print(f"🔘 Durum: {'AKTİF' if active else 'DURAKLATILDI'}")
    
    if active:
        # Aktifse Online ol
        await bot.change_presence(status=discord.Status.online, activity=discord.Game(name="War of Dragons"))
    else:
        # Pasifse Invisible (Görünmez) ol
        await bot.change_presence(status=discord.Status.invisible)
    
    print("━" * 40)
    
    setup_scheduler(bot, notification_channel)
    
    if notification_channel:
        status_text = "🟢 AKTİF (Online)" if active else "🔴 DURAKLATILDI (Gizli Mod)"
        await notification_channel.send(
            f"🐉 **Görev Takipçisi** sisteme giriş yaptı.\n"
            f"Durum: {status_text}\n"
            f"`!baslat` ile başlat | `!durdur` ile durdur"
        )


@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: discord.User):
    if user.bot:
        return
    await handle_reaction_add(reaction, user, bot)


# =============================================================================
# BAŞLAT / DURDUR (GÖRÜNÜM AYARLI)
# =============================================================================

@bot.command(name="baslat", aliases=["start"])
async def cmd_baslat(ctx: commands.Context):
    """Botu başlat ve online yap."""
    set_bot_active(True)
    
    # Botu YEŞİL (Online) yap ve aktivite ekle
    await bot.change_presence(status=discord.Status.online, activity=discord.Game(name="War of Dragons"))
    
    await ctx.send("🟢 **Bot BAŞLATILDI!** Bildirimler aktif ve çevrimiçiyim.")
    
    all_tasks = get_all_tasks_with_status()
    ready = [t for t in all_tasks if t.get('is_available') or t.get('is_open')]
    
    if ready:
        await ctx.send(f"📋 **{len(ready)}** görev hazır!")
        
        for task in ready:
            cat_name = task.get('category_name', '')
            category = next((c for c in get_all_categories() if c['name'] == cat_name), None)
            
            target = ctx.channel
            if category and category.get('discord_channel_id'):
                try:
                    ch = ctx.guild.get_channel(int(category['discord_channel_id']))
                    if ch:
                        target = ch
                except:
                    pass
            
            await send_lite_notification(target, task)
            await asyncio.sleep(MESSAGE_DELAY)
    else:
        await ctx.send("✅ Şu an yapılacak görev yok.")


@bot.command(name="durdur", aliases=["stop"])
async def cmd_durdur(ctx: commands.Context):
    """Botu durdur ve görünmez (offline gibi) yap."""
    set_bot_active(False)
    
    # Botu GRİ (Invisible/Offline görünümlü) yap
    await bot.change_presence(status=discord.Status.invisible)
    
    await ctx.send("🔴 **Bot DURAKLATILDI!** Arka planda takip devam ediyor ama ben uyuyorum. 💤\n`!baslat` yazarsan uyanırım.")


# =============================================================================
# DURUM KOMUTLARI
# =============================================================================

@bot.command(name="durum", aliases=["status"])
async def cmd_durum(ctx: commands.Context):
    """Tüm görevlerin durumu."""
    await send_status_overview(ctx.channel)


@bot.command(name="kontrol", aliases=["check"])
async def cmd_kontrol(ctx: commands.Context):
    """Hazır görevleri kontrol et."""
    channel_id = str(ctx.channel.id)
    
    category = get_category_by_channel_id(channel_id)
    
    if category:
        await check_single_category(ctx, category)
    else:
        await check_all_categories(ctx)


async def check_single_category(ctx, category: dict):
    """Tek kategori kontrol et."""
    cat_name = category['name']
    cat_id = category['id']
    
    tasks = get_tasks_by_category(cat_id)
    
    if not tasks:
        await ctx.send(f"📋 **{cat_name}** kategorisinde görev yok.")
        return
    
    tasks_with_status = [get_task_with_status(t) for t in tasks]
    ready = [t for t in tasks_with_status if t.get('is_available') or t.get('is_open')]
    
    if not ready:
        await ctx.send(f"✅ **{cat_name}** - Tüm görevler tamamlandı!")
        for t in tasks_with_status:
            await ctx.send(f"{t['status_emoji']} **{t['name']}** - {t['status_message']}")
            await asyncio.sleep(0.3)
        return
    
    await ctx.send(f"📋 **{cat_name}** - {len(ready)} görev hazır:")
    
    for task in ready:
        await send_lite_notification(ctx.channel, task)
        await asyncio.sleep(MESSAGE_DELAY)


async def check_all_categories(ctx):
    """Tüm kategorileri kontrol et."""
    all_tasks = get_all_tasks_with_status()
    ready = [t for t in all_tasks if t.get('is_available') or t.get('is_open')]
    
    if not ready:
        await ctx.send("✅ Yapılacak görev yok!")
        return
    
    grouped = {}
    for t in ready:
        cat = t.get('category_name', 'Bilinmeyen')
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(t)
    
    await ctx.send(f"📋 Toplam **{len(ready)}** görev hazır:")
    
    for cat_name, tasks in grouped.items():
        category = next((c for c in get_all_categories() if c['name'] == cat_name), None)
        target = ctx.channel
        
        if category and category.get('discord_channel_id'):
            try:
                ch = ctx.guild.get_channel(int(category['discord_channel_id']))
                if ch:
                    target = ch
            except:
                pass
        
        for task in tasks:
            await send_lite_notification(target, task)
            await asyncio.sleep(MESSAGE_DELAY)


# =============================================================================
# LİSTE KOMUTLARI
# =============================================================================

@bot.command(name="gunluk", aliases=["daily"])
async def cmd_gunluk(ctx):
    """Günlük görevler."""
    tasks = get_all_tasks_with_status()
    daily = [t for t in tasks if t['reset_type'] == 'daily']
    
    if not daily:
        await ctx.send("Günlük görev yok.")
        return
    
    for t in daily:
        s = "✅" if t.get('is_completed') else "❌"
        await ctx.send(f"{s} **{t['name']}** - {t['status_message']}")
        await asyncio.sleep(0.3)


@bot.command(name="haftalik", aliases=["weekly"])
async def cmd_haftalik(ctx):
    """Haftalık görevler."""
    from src.utils.time_utils import get_weekly_urgency_message
    
    tasks = get_all_tasks_with_status()
    weekly = [t for t in tasks if t['reset_type'] == 'weekly']
    
    if not weekly:
        await ctx.send("Haftalık görev yok.")
        return
    
    await ctx.send(get_weekly_urgency_message())
    
    for t in weekly:
        s = "✅" if t.get('is_completed') else "❌"
        await ctx.send(f"{s} **{t['name']}** - {t['status_message']}")
        await asyncio.sleep(0.3)


@bot.command(name="instancelar", aliases=["instances"])
async def cmd_instancelar(ctx):
    """Instance durumları."""
    tasks = get_all_tasks_with_status()
    instances = [t for t in tasks if t['reset_type'] == 'instance']
    
    if not instances:
        await ctx.send("Instance yok.")
        return
    
    for t in instances:
        cd = format_duration(t.get('cooldown_minutes', 0))
        active = format_duration(t.get('active_duration_minutes', 0))
        await ctx.send(f"{t['status_emoji']} **{t['name']}** - {t['status_message']} | Bekleme: {cd} | Açık: {active}")
        await asyncio.sleep(0.3)


# =============================================================================
# KURULUM
# =============================================================================

@bot.command(name="kanallari_esle", aliases=["sync_channels"])
async def cmd_sync_channels(ctx):
    """Kanalları oluştur."""
    if not ctx.guild:
        await ctx.send("❌ Sunucuda kullan!")
        return
    
    parent_id = get_setting('discord_parent_category_id', PARENT_CATEGORY_ID)
    if not parent_id:
        await ctx.send("⚠️ Önce: `!kategori_ayarla <id>`")
        return
    
    try:
        parent = ctx.guild.get_channel(int(parent_id))
        if not parent:
            await ctx.send("❌ Kategori bulunamadı")
            return
    except:
        await ctx.send("❌ Geçersiz ID")
        return
    
    await ctx.send(f"🔄 Kanallar eşleniyor...")
    
    categories = get_all_categories()
    created = existing = 0
    
    for cat in categories:
        name = cat['name'].lower().replace(' ', '-')
        
        if cat.get('discord_channel_id'):
            existing_ch = ctx.guild.get_channel(int(cat['discord_channel_id']))
            if existing_ch:
                existing += 1
                continue
        
        found = next((c for c in parent.channels if c.name == name), None)
        
        if found:
            set_category_channel(cat['id'], str(found.id))
            existing += 1
        else:
            try:
                ch = await ctx.guild.create_text_channel(name=name, category=parent)
                set_category_channel(cat['id'], str(ch.id))
                created += 1
                await asyncio.sleep(0.5)
            except:
                pass
    
    await ctx.send(f"✅ Oluşturulan: {created} | Mevcut: {existing}")


@bot.command(name="kategori_ayarla", aliases=["set_parent"])
async def cmd_set_parent(ctx, category_id: str = None):
    """Ana kategoriyi ayarla."""
    if not category_id:
        current = get_setting('discord_parent_category_id', '')
        await ctx.send(f"Mevcut: `{current or 'Ayarlanmamış'}`")
        return
    
    try:
        cat = ctx.guild.get_channel(int(category_id))
        if not isinstance(cat, discord.CategoryChannel):
            await ctx.send("❌ Bu bir kategori değil!")
            return
        
        set_setting('discord_parent_category_id', category_id)
        await ctx.send(f"✅ **{cat.name}** ayarlandı. `!kanallari_esle` çalıştır.")
    except:
        await ctx.send("❌ Geçersiz ID")


@bot.command(name="ayarlar", aliases=["settings"])
async def cmd_ayarlar(ctx):
    """Bot ayarları."""
    parent = get_setting('discord_parent_category_id', '') or 'Ayarlanmamış'
    active = "🟢 AKTİF" if is_bot_active() else "🔴 DURAKLATILDI"
    
    parent_name = 'Ayarlanmamış'
    if parent != 'Ayarlanmamış':
        try:
            cat = ctx.guild.get_channel(int(parent))
            parent_name = cat.name if cat else parent
        except:
            pass
    
    await ctx.send(
        f"⚙️ **Ayarlar**\n"
        f"📁 Ana Kategori: **{parent_name}**\n"
        f"🔘 Durum: {active}\n"
        f"🗄️ PostgreSQL | ⚡ 1dk | 🔄 60dk"
    )


@bot.command(name="kanal_debug", aliases=["channel_debug"])
async def cmd_kanal_debug(ctx):
    """Kanal eşleştirmelerini göster."""
    channel_id = str(ctx.channel.id)
    
    categories = get_all_categories()
    
    lines = [
        f"🔍 **Kanal Debug**",
        f"📍 `#{ctx.channel.name}` (ID: `{channel_id}`)",
        ""
    ]
    
    found = False
    for cat in categories:
        cat_channel = cat.get('discord_channel_id')
        if cat_channel and str(cat_channel) == channel_id:
            lines.append(f"✅ **{cat['name']}** → BU KANAL")
            found = True
        elif cat_channel:
            lines.append(f"📁 {cat['name']} → `{cat_channel}`")
        else:
            lines.append(f"⚠️ {cat['name']} → Atanmamış")
    
    if not found:
        lines.append("")
        lines.append("⚠️ Bu kanal kategoriye atanmamış!")
    
    await ctx.send("\n".join(lines))


@bot.command(name="yardim", aliases=["help_tasks", "komutlar"])
async def cmd_yardim(ctx):
    """Yardım."""
    await ctx.send(
        "🐉 **Komutlar**\n"
        "`!durum` / `!kontrol` / `!gunluk` / `!haftalik` / `!instancelar`\n"
        "\n🔘 `!baslat` / `!durdur`\n"
        "🔧 `!kategori_ayarla` / `!kanallari_esle` / `!kanal_debug` / `!ayarlar`\n"
        "⚠️ `!veritabani_sifirla` - Veritabanını sıfırla (DİKKAT!)\n"
        "\n**Butonlar:** ✅ Yaptım | ❌ Geç | ⏰ Hatırlat"
    )


@bot.command(name="veritabani_sifirla", aliases=["reset_db"])
async def cmd_reset_db(ctx):
    """
    Veritabanı tablolarını sıfırla ve yeniden oluştur.
    DİKKAT: Tüm veriler silinir!
    """
    await ctx.send("⚠️ **DİKKAT:** Veritabanını sıfırlamak üzeresin!\nTüm görevler ve durumlar silinecek.\n\n5 saniye içinde devam ediliyor...")
    await asyncio.sleep(5)
    
    await ctx.send("🔄 Veritabanı sıfırlanıyor...")
    
    try:
        from src.database.models import Base, engine, SessionLocal, seed_database
        
        if not engine:
            await ctx.send("❌ DATABASE_URL ayarlanmamış!")
            return
        
        # Tüm tabloları sil
        await ctx.send("🗑️ Tablolar siliniyor...")
        Base.metadata.drop_all(bind=engine)
        
        # Tabloları yeniden oluştur
        await ctx.send("📦 Tablolar oluşturuluyor...")
        Base.metadata.create_all(bind=engine)
        
        # Varsayılan verileri ekle
        await ctx.send("🌱 Varsayılan veriler ekleniyor...")
        seed_database()
        
        await ctx.send(
            "✅ **Veritabanı başarıyla sıfırlandı!**\n"
            "Tüm tablolar yeniden oluşturuldu.\n"
            "Varsayılan kategoriler ve görevler eklendi.\n\n"
            "`!kanallari_esle` komutunu çalıştırarak kanalları eşleştir."
        )
        
    except Exception as e:
        await ctx.send(f"❌ **Hata:** {e}")
        import traceback
        traceback.print_exc()




def run_bot():
    if not DISCORD_TOKEN:
        print("❌ DISCORD_TOKEN ayarlanmamış!")
        return
    
    if not DATABASE_URL:
        print("⚠️ DATABASE_URL ayarlanmamış!")
    
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    run_bot()
