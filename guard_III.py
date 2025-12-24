import discord
from discord.ext import commands
from base_sentinel import BaseSentinel
from utils import create_embed
import os
import asyncio

class GuardIII(BaseSentinel):
    def __init__(self, log_bot):
        intents = discord.Intents.default()
        intents.members = True      # Üye katılımlarını izlemek için
        intents.moderation = True   # Audit Log için
        super().__init__(command_prefix="!", intents=intents, bot_name="GuardIII")
        self.log_bot = log_bot

        # .env'den ayarları yükle
        self.whitelist = [int(user_id) for user_id in os.getenv("WHITELIST_USERS", "").split(',') if user_id]

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # Eğer katılan üye bir bot değilse, işlemi sonlandır.
        if not member.bot:
            return

        guild = member.guild
        inviter = None

        await asyncio.sleep(2) # Audit log'un güncellenmesi için bekle

        # Denetim kaydından botu kimin eklediğini bul
        try:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.bot_add):
                if entry.target.id == member.id:
                    inviter = entry.user
                    break
        except discord.Forbidden:
            self.logger.error("Denetim kaydını okuma iznim yok.")
            return

        # Botu sunucudan at
        try:
            await member.kick(reason="Guard III: Sunucuya yetkisiz bot eklenemez.")
        except discord.Forbidden:
            self.logger.error(f"{member.name} botu atılamadı, yetkim yetersiz.")
            # Bot atılamasa bile ekleyeni cezalandırmaya devam et

        if inviter is None:
            log_description = (
                f"**Eklenen Bot:** {member.mention} (`{member.id}`)\n"
                f"**Durum:** Bot sunucudan atıldı, ancak ekleyen kişi denetim kaydından bulunamadı."
            )
            log_embed = create_embed(
                title="Guard III - Yetkisiz Bot Eklendi",
                description=log_description,
                color=discord.Color.orange()
            )
            await self.log_bot.log_action("guard", log_embed)
            return

        # Eğer ekleyen kişi beyaz listede ise veya botun kendisi ise işlem yapma
        if inviter.id in self.whitelist or inviter.id == self.user.id:
            log_description = (
                f"**Eklenen Bot:** {member.mention} (`{member.id}`)\n"
                f"**Ekleyen Kişi:** {inviter.mention} (Beyaz Listede)\n"
                f"**Durum:** Bot sunucudan atıldı, ekleyen kişi beyaz listede olduğu için ceza uygulanmadı."
            )
            log_embed = create_embed(
                title="Guard III - Beyaz Listeden Bot Eklendi",
                description=log_description,
                color=discord.Color.green(),
                author=inviter
            )
            await self.log_bot.log_action("guard", log_embed)
            return

        # Ekleyen kişiyi kalıcı olarak yasakla
        try:
            await inviter.ban(reason="Guard III: Sunucuya yetkisiz bot ekleme.")
        except discord.Forbidden:
            self.logger.error(f"{inviter.name} yasaklanamadı, yetkim yetersiz.")

        # Tüm işlemi logla
        final_log_description = (
            f"**Eklenen Bot:** {member.mention} (`{member.id}`)\n"
            f"**Ekleyen Kişi:** {inviter.mention} (`{inviter.id}`)\n"
            f"**Uygulanan Ceza:**\n"
            f"- Eklenen bot sunucudan atıldı.\n"
            f"- Botu ekleyen kullanıcı kalıcı olarak yasaklandı."
        )
        final_log_embed = create_embed(
            title="Guard III - AĞIR İHLAL: Yetkisiz Bot Ekleme",
            description=final_log_description,
            color=discord.Color.red(),
            author=inviter
        )
        await self.log_bot.log_action("guard", final_log_embed)
