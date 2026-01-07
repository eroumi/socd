import discord
from discord.ext import commands
from base_sentinel import BaseSentinel
from utils import create_embed, send_dm_notification
import os
import asyncio
import database
import time

class GuardIII(BaseSentinel):
    def __init__(self, log_bot):
        intents = discord.Intents.default()
        intents.members = True
        intents.moderation = True
        super().__init__(command_prefix="!", intents=intents, bot_name="GuardIII")
        self.log_bot = log_bot
        self.whitelist = [int(user_id) for user_id in os.getenv("WHITELIST_USERS", "").split(',') if user_id]

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not member.bot: return

        guild = member.guild
        inviter = None
        await asyncio.sleep(2)

        try:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.bot_add):
                if entry.target.id == member.id:
                    inviter = entry.user
                    break
        except discord.Forbidden: return

        try: await member.kick(reason="Guard III: Yetkisiz bot.")
        except discord.Forbidden: pass

        if inviter is None or inviter.id in self.whitelist or inviter.id == self.user.id:
            return

        ban_reason = "Guard III: Sunucuya yetkisiz bot ekleme."
        try:
            await send_dm_notification(inviter, guild.name, "Yasaklanma", ban_reason, self.user)
            await inviter.ban(reason=ban_reason)
            database.add_record("bans", {"user_id": inviter.id, "moderator_id": self.user.id, "reason": ban_reason, "timestamp": int(time.time())})

            log_embed = create_embed("Guard III - AĞIR İHLAL", f"{inviter.mention} yetkisiz bot eklediği için yasaklandı.", discord.Color.red(), author=inviter)
            await self.log_bot.log_action("guard", log_embed)
        except discord.Forbidden:
            self.logger.error(f"{inviter.name} yasaklanamadı.")
