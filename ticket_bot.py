import discord
from discord import app_commands, ui
from discord.ext import commands
from base_sentinel import BaseSentinel
from utils import create_embed
import os
import asyncio
import database

class TicketView(ui.View):
    def __init__(self, ticket_bot_instance):
        super().__init__(timeout=None)
        self.bot = ticket_bot_instance

    @ui.button(label="Destek Talebi Oluştur", style=discord.ButtonStyle.green, custom_id="create_ticket_button")
    async def create_ticket(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)
        user = interaction.user
        guild = interaction.guild

        if database.get_open_ticket_by_user(user.id):
            await interaction.followup.send("Zaten açık bir destek talebiniz var.", ephemeral=True)
            return

        try:
            category = discord.utils.get(guild.categories, id=int(os.getenv("TICKET_CATEGORY_ID")))
            support_role = guild.get_role(int(os.getenv("TICKET_SUPPORT_ROLE_ID")))
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            channel = await guild.create_text_channel(f"ticket-{user.name}", category=category, overwrites=overwrites)

            database.create_ticket_record(user.id, channel.id)

            await channel.send(embed=create_embed("Destek Talebi", f"Merhaba {user.mention}, ekibimiz sizinle ilgilenecek.", discord.Color.blurple()), view=CloseTicketView(self.bot))
            await interaction.followup.send(f"Talebiniz oluşturuldu: {channel.mention}", ephemeral=True)
        except Exception as e:
            self.bot.logger.error(f"Ticket oluşturma hatası: {e}", exc_info=True)
            await interaction.followup.send("Bir hata oluştu.", ephemeral=True)

class CloseTicketView(ui.View):
    def __init__(self, ticket_bot_instance):
        super().__init__(timeout=None)
        self.bot = ticket_bot_instance

    @ui.button(label="Talebi Kapat", style=discord.ButtonStyle.red, custom_id="close_ticket_button")
    async def close_ticket(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Talep 5 saniye içinde kapatılacak...")
        database.close_ticket_record(interaction.channel.id)
        await asyncio.sleep(5)
        await interaction.channel.delete()

class TicketBot(BaseSentinel):
    def __init__(self, log_bot):
        intents = discord.Intents.default()
        intents.dm_messages = True
        intents.messages = True
        super().__init__(command_prefix="/", intents=intents, bot_name="TicketBot")
        self.log_bot = log_bot
        self.persistent_views_added = False

    async def setup_hook(self):
        if not self.persistent_views_added:
            self.add_view(TicketView(self))
            self.add_view(CloseTicketView(self))
            self.persistent_views_added = True

    @app_commands.command(name="ticketpanel", description="Destek talebi panelini gönderir.")
    @app_commands.default_permissions(administrator=True)
    async def ticketpanel(self, interaction: discord.Interaction):
        await interaction.channel.send(embed=create_embed("Destek Merkezi", "Talep oluşturmak için butona tıklayın.", discord.Color.dark_blue()), view=TicketView(self))
        await interaction.response.send_message("Panel oluşturuldu.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot: return
        guild = self.get_guild(int(os.getenv("GUILD_ID")))
        if not guild: return

        # DM'den kanala
        if isinstance(message.channel, discord.DMChannel):
            ticket = database.get_open_ticket_by_user(message.author.id)
            if ticket:
                channel = guild.get_channel(ticket['channel_id'])
                if channel:
                    await channel.send(embed=create_embed("Kullanıcıdan Mesaj", message.content, discord.Color.green(), author=message.author))

        # Kanaldan DM'e
        else:
            ticket = database.get_open_ticket_by_channel(message.channel.id)
            if ticket:
                user = guild.get_member(ticket['user_id'])
                support_role_id = int(os.getenv("TICKET_SUPPORT_ROLE_ID"))
                if user and any(role.id == support_role_id for role in message.author.roles):
                    try:
                        await user.send(embed=create_embed("Destek Ekibinden Cevap", message.content, discord.Color.gold(), author=message.author))
                    except discord.Forbidden:
                        await message.channel.send("Kullanıcının DM'leri kapalı.", delete_after=10)
