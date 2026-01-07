import discord
from discord import app_commands
from base_sentinel import BaseSentinel
from utils import create_embed, send_dm_notification
import os
import time
from datetime import timedelta
import database

def parse_duration(duration_str: str) -> timedelta:
    try:
        unit = duration_str[-1].lower()
        value = int(duration_str[:-1])
        if unit == 'm': return timedelta(minutes=value)
        elif unit == 'h': return timedelta(hours=value)
        elif unit == 'd': return timedelta(days=value)
    except (ValueError, IndexError): return None
    return None

class SystemBot(BaseSentinel):
    def __init__(self, log_bot):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="/", intents=intents, bot_name="SystemBot")
        self.log_bot = log_bot

    async def setup_hook(self):
        self.tree.copy_global_to(guild=self.guild_id)
        await self.tree.sync(guild=self.guild_id)

    @app_commands.command(name="kick", description="Belirtilen üyeyi sunucudan atar.")
    @app_commands.describe(member="Atılacak üye", reason="Atılma sebebi")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Belirtilmedi"):
        if member.id in [int(uid) for uid in os.getenv("WHITELIST_USERS", "").split(',')]:
            await interaction.response.send_message("Bu kullanıcı beyaz listede, işlem yapılamaz.", ephemeral=True)
            return
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message("Bu kullanıcının rolü sizden yüksek veya aynı.", ephemeral=True)
            return
        try:
            await send_dm_notification(member, interaction.guild.name, "Atılma", reason, interaction.user)
            await member.kick(reason=reason)
            log_desc = f"**Yetkili:** {interaction.user.mention}\n**Kullanıcı:** {member.mention}\n**Sebep:** {reason}"
            log_embed = create_embed("Kullanıcı Atıldı", log_desc, discord.Color.orange(), author=interaction.user)
            await self.log_bot.log_action("mod", log_embed)
            await interaction.response.send_message(embed=log_embed)
        except discord.Forbidden:
            await interaction.response.send_message("Bu kullanıcıyı atmak için yetkim yok.", ephemeral=True)

    @app_commands.command(name="ban", description="Belirtilen üyeyi sunucudan yasaklar.")
    @app_commands.describe(member="Yasaklanacak üye", reason="Yasaklama sebebi")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Belirtilmedi"):
        if member.id in [int(uid) for uid in os.getenv("WHITELIST_USERS", "").split(',')]:
            await interaction.response.send_message("Bu kullanıcı beyaz listede, işlem yapılamaz.", ephemeral=True)
            return
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message("Bu kullanıcının rolü sizden yüksek veya aynı.", ephemeral=True)
            return
        try:
            await send_dm_notification(member, interaction.guild.name, "Yasaklanma", reason, interaction.user)
            await member.ban(reason=reason)
            database.add_record("bans", {"user_id": member.id, "moderator_id": interaction.user.id, "reason": reason, "timestamp": int(time.time())})
            log_desc = f"**Yetkili:** {interaction.user.mention}\n**Kullanıcı:** {member.mention}\n**Sebep:** {reason}"
            log_embed = create_embed("Kullanıcı Yasaklandı", log_desc, discord.Color.red(), author=interaction.user)
            await self.log_bot.log_action("mod", log_embed)
            await interaction.response.send_message(embed=log_embed)
        except discord.Forbidden:
            await interaction.response.send_message("Bu kullanıcıyı yasaklamak için yetkim yok.", ephemeral=True)

    @app_commands.command(name="unban", description="Belirtilen kullanıcının yasağını kaldırır.")
    @app_commands.describe(user_id="Yasağı kaldırılacak kullanıcının ID'si")
    @app_commands.default_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: str):
        try:
            user = await self.fetch_user(int(user_id))
            await interaction.guild.unban(user)
            database.deactivate_record("bans", user.id)
            log_desc = f"**Yetkili:** {interaction.user.mention}\n**Kullanıcı:** {user.mention}"
            log_embed = create_embed("Yasak Kaldırıldı", log_desc, discord.Color.green(), author=interaction.user)
            await self.log_bot.log_action("mod", log_embed)
            await interaction.response.send_message(embed=log_embed)
        except (ValueError, discord.NotFound):
            await interaction.response.send_message("Geçerli bir kullanıcı ID'si girin veya yasaklı değil.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Yasak kaldırmak için yetkim yok.", ephemeral=True)

    @app_commands.command(name="warn", description="Bir kullanıcıyı uyarır.")
    @app_commands.describe(member="Uyarılacak üye", reason="Uyarı sebebi")
    @app_commands.default_permissions(manage_messages=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        database.add_record("warnings", {"user_id": member.id, "moderator_id": interaction.user.id, "reason": reason, "timestamp": int(time.time())})
        await send_dm_notification(member, interaction.guild.name, "Uyarı", reason, interaction.user)
        log_desc = f"**Yetkili:** {interaction.user.mention}\n**Kullanıcı:** {member.mention}\n**Sebep:** {reason}"
        log_embed = create_embed("Kullanıcı Uyarıldı", log_desc, discord.Color.yellow(), author=interaction.user)
        await self.log_bot.log_action("mod", log_embed)
        await interaction.response.send_message(embed=log_embed)

    @app_commands.command(name="timeout", description="Bir üyeye zaman aşımı uygular.")
    @app_commands.describe(member="Susturulacak üye", duration="Süre (örn: 10m, 2h, 7d)", reason="Sebep")
    @app_commands.default_permissions(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, duration: str, reason: str):
        delta = parse_duration(duration)
        if not delta or delta.days > 28:
            await interaction.response.send_message("Geçersiz süre formatı.", ephemeral=True)
            return
        try:
            await member.timeout(delta, reason=reason)
            expires_at = int(time.time()) + delta.total_seconds()
            database.add_record("timeouts", {"user_id": member.id, "moderator_id": interaction.user.id, "reason": reason, "timestamp": int(time.time()), "expires_at": expires_at})
            await send_dm_notification(member, interaction.guild.name, "Susturulma", f"{reason} ({duration})", interaction.user)
            log_desc = f"**Yetkili:** {interaction.user.mention}\n**Kullanıcı:** {member.mention}\n**Süre:** {duration}\n**Sebep:** {reason}"
            log_embed = create_embed("Kullanıcı Susturuldu", log_desc, discord.Color.light_grey(), author=interaction.user)
            await self.log_bot.log_action("mod", log_embed)
            await interaction.response.send_message(embed=log_embed)
        except discord.Forbidden:
            await interaction.response.send_message("Bu üyeye zaman aşımı uygulamak için yetkim yok.", ephemeral=True)

    @app_commands.command(name="untimeout", description="Bir üyenin zaman aşımını kaldırır.")
    @app_commands.describe(member="Zaman aşımı kaldırılacak üye")
    @app_commands.default_permissions(moderate_members=True)
    async def untimeout(self, interaction: discord.Interaction, member: discord.Member):
        try:
            await member.timeout(None, reason="Zaman aşımı kaldırıldı.")
            database.deactivate_record("timeouts", member.id)
            await send_dm_notification(member, interaction.guild.name, "Susturma Kaldırıldı", "Zaman aşımınız kaldırıldı.", interaction.user)
            log_desc = f"**Yetkili:** {interaction.user.mention}\n**Kullanıcı:** {member.mention}"
            log_embed = create_embed("Zaman Aşımı Kaldırıldı", log_desc, discord.Color.dark_grey(), author=interaction.user)
            await self.log_bot.log_action("mod", log_embed)
            await interaction.response.send_message(embed=log_embed)
        except discord.Forbidden:
            await interaction.response.send_message("Bu üyenin zaman aşımını kaldırmak için yetkim yok.", ephemeral=True)

    @app_commands.command(name="clear", description="Belirtilen miktarda mesajı kanaldan siler.")
    @app_commands.describe(amount="Silinecek mesaj sayısı (1-100)")
    @app_commands.default_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.response.send_message(f"{len(deleted)} adet mesaj silindi.", ephemeral=True, delete_after=5)

    @app_commands.command(name="warnlist", description="Bir üyenin geçmiş uyarılarını listeler.")
    @app_commands.describe(member="Uyarıları listelenecek üye")
    @app_commands.default_permissions(manage_messages=True)
    async def warnlist(self, interaction: discord.Interaction, member: discord.Member):
        warnings = database.get_warnings_for_user(member.id)
        if not warnings:
            await interaction.response.send_message(f"{member.mention} kullanıcısının hiç uyarısı yok.", ephemeral=True)
            return
        embed = discord.Embed(title=f"{member.name} Uyarı Listesi", color=discord.Color.yellow())
        description = ""
        for warn in warnings:
            mod = await self.fetch_user(warn['moderator_id'])
            timestamp = f"<t:{warn['timestamp']}:F>"
            description += f"**ID: {warn['id']}** | Yetkili: {mod.mention}\n**Sebep:** {warn['reason']}\n\n"
        embed.description = description
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="unwarn", description="Bir üyenin uyarısını ID ile kaldırır.")
    @app_commands.describe(warning_id="Kaldırılacak uyarının ID'si")
    @app_commands.default_permissions(manage_messages=True)
    async def unwarn(self, interaction: discord.Interaction, warning_id: int):
        warning_record = database.get_warning_by_id(warning_id)
        if not warning_record:
            await interaction.response.send_message(f"`{warning_id}` ID'li bir uyarı bulunamadı.", ephemeral=True)
            return
        user_id = warning_record['user_id']
        member = interaction.guild.get_member(user_id)
        if not database.delete_warning(warning_id):
            await interaction.response.send_message("Uyarı silinirken bir hata oluştu.", ephemeral=True)
            return
        log_desc = f"**Yetkili:** {interaction.user.mention}\n**Kaldırılan Uyarı ID:** `{warning_id}`\n**Kullanıcı:** {member.mention if member else user_id}"
        log_embed = create_embed("Uyarı Kaldırıldı", log_desc, discord.Color.light_grey(), author=interaction.user)
        await self.log_bot.log_action("mod", log_embed)
        await interaction.response.send_message(embed=log_embed)
        if member:
            await send_dm_notification(member, interaction.guild.name, "Uyarı Kaldırıldı", f"`{warning_id}` ID'li uyarınız kaldırıldı.", interaction.user)

    @app_commands.command(name="banlist", description="Sunucudaki aktif yasaklamaları listeler.")
    @app_commands.default_permissions(ban_members=True)
    async def banlist(self, interaction: discord.Interaction):
        bans = database.get_active_records("bans")
        if not bans:
            await interaction.response.send_message("Aktif yasaklama yok.", ephemeral=True)
            return
        embed = discord.Embed(title="Aktif Yasaklama Listesi", color=discord.Color.red())
        description = ""
        for ban in bans:
            user = await self.fetch_user(ban['user_id'])
            mod = await self.fetch_user(ban['moderator_id'])
            timestamp = f"<t:{ban['timestamp']}:R>"
            description += f"- **{user.name}** (`{user.id}`) | Yetkili: {mod.mention} | Sebep: {ban['reason']}\n"
        embed.description = description
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="timeoutlist", description="Sunucudaki aktif zaman aşımlarını listeler.")
    @app_commands.default_permissions(moderate_members=True)
    async def timeoutlist(self, interaction: discord.Interaction):
        timeouts = database.get_active_records("timeouts")
        if not timeouts:
            await interaction.response.send_message("Aktif zaman aşımı yok.", ephemeral=True)
            return
        embed = discord.Embed(title="Aktif Zaman Aşımları", color=discord.Color.light_grey())
        description = ""
        for to in timeouts:
            user = await self.fetch_user(to['user_id'])
            mod = await self.fetch_user(to['moderator_id'])
            expires = f"<t:{to['expires_at']}:R>"
            description += f"- **{user.name}** | Yetkili: {mod.mention} | Bitiş: {expires}\n"
        embed.description = description
        await interaction.response.send_message(embed=embed, ephemeral=True)
