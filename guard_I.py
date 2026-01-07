import discord
from discord.ext import commands
from base_sentinel import BaseSentinel
from utils import create_embed, send_dm_notification
import os
import asyncio
from collections import defaultdict
import time
import database

class GuardI(BaseSentinel):
    def __init__(self, log_bot):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.moderation = True
        super().__init__(command_prefix="!", intents=intents, bot_name="GuardI")
        self.log_bot = log_bot
        self.whitelist = [int(user_id) for user_id in os.getenv("WHITELIST_USERS", "").split(',') if user_id]
        self.violation_limit = int(os.getenv("VIOLATION_LIMIT", 3))
        self.time_window = int(os.getenv("VIOLATION_TIME_WINDOW_HOURS", 24)) * 3600
        self.violations = defaultdict(list)

    async def check_audit_log_and_punish(self, guild, action_type, target_object):
        await asyncio.sleep(2)
        entry = None
        async for e in guild.audit_logs(limit=1, action=action_type):
            if e.target.id == target_object.id:
                entry = e
                break
        if entry is None or entry.user.id in self.whitelist or entry.user.id == self.user.id:
            return

        user = entry.user
        current_time = time.time()
        self.violations[user.id] = [t for t in self.violations[user.id] if current_time - t < self.time_window]
        self.violations[user.id].append(current_time)

        rollback_successful = await self.rollback_action(entry, target_object)

        log_description = f"**Kullanıcı:** {user.mention} (`{user.id}`)\n..."
        log_embed = create_embed("Guard I - Sunucu İhlali Tespit Edildi", log_description, discord.Color.orange(), author=user)
        await self.log_bot.log_action("guard", log_embed)

        if len(self.violations[user.id]) >= self.violation_limit:
            self.violations[user.id].clear()
            kick_reason = f"Guard I: {self.violation_limit} sunucu ihlali yapıldı."
            try:
                await send_dm_notification(user, guild.name, "Atılma", kick_reason, self.user)
                await guild.kick(user, reason=kick_reason)

                database.add_record("warnings", {"user_id": user.id, "moderator_id": self.user.id, "reason": f"(Otomatik Kick) {kick_reason}", "timestamp": int(time.time())})
                kick_log_embed = create_embed("Guard I - Kullanıcı Atıldı", f"{user.mention} atıldı.", discord.Color.red(), author=user)
                await self.log_bot.log_action("guard", kick_log_embed)
            except discord.Forbidden:
                self.logger.error(f"{user.name} atılamadı.")

    async def rollback_action(self, entry, target):
        try:
            if entry.action == discord.AuditLogAction.channel_create: await target.delete()
            elif entry.action == discord.AuditLogAction.role_create: await target.delete()
            return True
        except Exception: return False

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        await self.check_audit_log_and_punish(channel.guild, discord.AuditLogAction.channel_create, channel)
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        await self.check_audit_log_and_punish(role.guild, discord.AuditLogAction.role_create, role)
    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        if before.name != after.name:
             await self.check_audit_log_and_punish(after, discord.AuditLogAction.guild_update, after)
    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        await self.check_audit_log_and_punish(after.guild, discord.AuditLogAction.role_update, after)
