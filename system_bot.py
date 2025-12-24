import discord
from discord import app_commands
from base_sentinel import BaseSentinel
from utils import create_embed
import os

class SystemBot(BaseSentinel):
    def __init__(self, log_bot):
        intents = discord.Intents.default()
        intents.members = True # Üyeleri bulabilmek için
        super().__init__(command_prefix="/", intents=intents, bot_name="SystemBot")
        self.log_bot = log_bot

    async def setup_hook(self):
        # Komutları global olarak değil, sadece belirtilen sunucuda senkronize et.
        # Bu, on_ready içinde zaten yapılıyor ama burada tekrar teyit edilebilir.
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
            await interaction.response.send_message("Bu kullanıcının rolü sizden yüksek veya aynı, işlem yapamazsınız.", ephemeral=True)
            return

        try:
            await member.kick(reason=reason)

            # Loglama
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
            await interaction.response.send_message("Bu kullanıcının rolü sizden yüksek veya aynı, işlem yapamazsınız.", ephemeral=True)
            return

        try:
            await member.ban(reason=reason)

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

            log_desc = f"**Yetkili:** {interaction.user.mention}\n**Kullanıcı:** {user.mention}"
            log_embed = create_embed("Yasak Kaldırıldı", log_desc, discord.Color.green(), author=interaction.user)
            await self.log_bot.log_action("mod", log_embed)

            await interaction.response.send_message(embed=log_embed)
        except discord.NotFound:
            await interaction.response.send_message("Bu ID'ye sahip bir yasaklama bulunamadı.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Yasak kaldırmak için yetkim yok.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Lütfen geçerli bir kullanıcı ID'si girin.", ephemeral=True)

    @app_commands.command(name="clear", description="Belirtilen miktarda mesajı kanaldan siler.")
    @app_commands.describe(amount="Silinecek mesaj sayısı (1-100)")
    @app_commands.default_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
        try:
            deleted = await interaction.channel.purge(limit=amount)

            log_desc = f"**Yetkili:** {interaction.user.mention}\n**Kanal:** {interaction.channel.mention}\n**Silinen Mesaj:** {len(deleted)} adet"
            log_embed = create_embed("Mesajlar Silindi", log_desc, discord.Color.blue(), author=interaction.user)
            await self.log_bot.log_action("mod", log_embed)

            await interaction.response.send_message(f"{len(deleted)} adet mesaj başarıyla silindi.", ephemeral=True, delete_after=5)
        except discord.Forbidden:
            await interaction.response.send_message("Mesajları silmek için yetkim yok.", ephemeral=True)
