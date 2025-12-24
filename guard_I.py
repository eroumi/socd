import discord
from discord.ext import commands
from base_sentinel import BaseSentinel
from utils import create_embed
import os
import asyncio
from collections import defaultdict
import time

class GuardI(BaseSentinel):
    def __init__(self, log_bot):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.moderation = True  # Audit Log için gerekli
        super().__init__(command_prefix="!", intents=intents, bot_name="GuardI")
        self.log_bot = log_bot

        # .env'den ayarları yükle
        self.whitelist = [int(user_id) for user_id in os.getenv("WHITELIST_USERS", "").split(',') if user_id]
        self.violation_limit = int(os.getenv("VIOLATION_LIMIT", 3))
        self.time_window = int(os.getenv("VIOLATION_TIME_WINDOW_HOURS", 24)) * 3600

        self.violations = defaultdict(list)
        self.logger.info(f"Whitelist loaded: {self.whitelist}")

    async def check_audit_log_and_punish(self, guild, action_type, target_object):
        """
        Denetim kaydını kontrol eder, fail beyaz listede değilse işlemi geri alır ve cezalandırır.
        """
        await asyncio.sleep(2)  # Audit log'un güncellenmesi için kısa bir bekleme

        entry = None
        async for e in guild.audit_logs(limit=1, action=action_type):
            if e.target.id == target_object.id:
                entry = e
                break

        if entry is None or entry.user.id == self.user.id or entry.user.id in self.whitelist:
            return

        user = entry.user

        # İhlal takibi
        current_time = time.time()
        self.violations[user.id] = [t for t in self.violations[user.id] if current_time - t < self.time_window]
        self.violations[user.id].append(current_time)

        # Geri alma işlemini gerçekleştir ve logla
        rollback_successful = await self.rollback_action(entry, target_object)

        log_description = (
            f"**Kullanıcı:** {user.mention} (`{user.id}`)\n"
            f"**Eylem:** {action_type.name.replace('_', ' ').title()}\n"
            f"**Hedef:** {getattr(target_object, 'name', str(target_object.id))}\n"
            f"**İhlal Sayısı:** {len(self.violations[user.id])}/{self.violation_limit}\n"
            f"**Geri Alma Durumu:** {'Başarılı' if rollback_successful else 'Başarısız'}"
        )

        log_embed = create_embed(
            title="Guard I - Sunucu İhlali Tespit Edildi",
            description=log_description,
            color=discord.Color.orange(),
            author=user
        )
        await self.log_bot.log_action("guard", log_embed)

        # Ceza
        if len(self.violations[user.id]) >= self.violation_limit:
            self.violations[user.id].clear()
            try:
                await guild.kick(user, reason=f"Guard I: {self.violation_limit} sunucu ihlali yapıldı.")
                kick_log_embed = create_embed(
                    title="Guard I - Kullanıcı Atıldı",
                    description=f"{user.mention} adlı kullanıcı, {self.violation_limit} ihlale ulaştığı için sunucudan atıldı.",
                    color=discord.Color.red(),
                    author=user
                )
                await self.log_bot.log_action("guard", kick_log_embed)
            except discord.Forbidden:
                self.logger.error(f"{user.name} atılamadı, yetkim yetersiz.")

    async def rollback_action(self, entry, target):
        """Yapılan işlemi geri alır."""
        try:
            if entry.action == discord.AuditLogAction.channel_create:
                await target.delete(reason="Guard I: Yetkisiz oluşturma.")
            elif entry.action == discord.AuditLogAction.role_create:
                await target.delete(reason="Guard I: Yetkisiz oluşturma.")
            elif entry.action == discord.AuditLogAction.guild_update:
                before = entry.before
                await entry.target.edit(**{attr: getattr(before, attr) for attr, val in entry.changes[0].items()})
            elif entry.action == discord.AuditLogAction.role_update:
                 before = entry.before
                 # Sadece temel özellikleri geri almayı dene
                 await target.edit(name=before.name, permissions=before.permissions, color=before.color, hoist=before.hoist, mentionable=before.mentionable, reason="Guard I: Yetkisiz güncelleme.")
            # Silme işlemleri için geri alma (rollback) daha karmaşıktır ve önbellek gerektirir.
            # Şimdilik sadece oluşturma ve güncelleme geri alınıyor.
            return True
        except Exception as e:
            self.logger.error(f"Geri alma işlemi sırasında hata: {e}", exc_info=True)
            return False

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        await self.check_audit_log_and_punish(channel.guild, discord.AuditLogAction.channel_create, channel)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        await self.check_audit_log_and_punish(role.guild, discord.AuditLogAction.role_create, role)

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        # Sadece temel ayarlar izleniyor.
        if before.name != after.name or before.icon != after.icon:
             await self.check_audit_log_and_punish(after, discord.AuditLogAction.guild_update, after)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        await self.check_audit_log_and_punish(after.guild, discord.AuditLogAction.role_update, after)
