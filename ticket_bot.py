import discord
from discord.ext import commands
from discord import app_commands, ui
from base_sentinel import BaseSentinel
from utils import create_embed
import os
import asyncio

# Aktif ticketları takip etmek için (user_id: channel_id)
active_tickets = {}

class TicketView(ui.View):
    def __init__(self, ticket_bot_instance):
        super().__init__(timeout=None)
        self.bot = ticket_bot_instance

    @ui.button(label="Destek Talebi Oluştur", style=discord.ButtonStyle.green, custom_id="create_ticket_button", emoji="🎟️")
    async def create_ticket(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer(ephemeral=True)

        user = interaction.user
        guild = interaction.guild

        if user.id in active_tickets:
            existing_channel = guild.get_channel(active_tickets[user.id])
            if existing_channel:
                await interaction.followup.send(f"Zaten açık bir destek talebiniz var: {existing_channel.mention}", ephemeral=True)
                return

        try:
            category_id = int(os.getenv("TICKET_CATEGORY_ID"))
            support_role_id = int(os.getenv("TICKET_SUPPORT_ROLE_ID"))

            category = discord.utils.get(guild.categories, id=category_id)
            support_role = guild.get_role(support_role_id)

            if not category or not support_role:
                await interaction.followup.send("Ticket sistemi için gerekli kategori veya rol bulunamadı. Lütfen yöneticiye bildirin.", ephemeral=True)
                return

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }

            channel_name = f"ticket-{user.name}"
            ticket_channel = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)

            active_tickets[user.id] = ticket_channel.id

            # Kanal içine mesaj ve kapatma butonu
            welcome_embed = create_embed("Destek Talebi Oluşturuldu", f"Merhaba {user.mention}, destek ekibimiz en kısa sürede sizinle ilgilenecektir. Lütfen sorununuzu buraya yazın.", discord.Color.blurple())
            await ticket_channel.send(embed=welcome_embed, view=CloseTicketView(self.bot))

            await interaction.followup.send(f"Destek talebiniz oluşturuldu: {ticket_channel.mention}", ephemeral=True)

        except Exception as e:
            self.bot.logger.error(f"Ticket oluşturulurken hata: {e}", exc_info=True)
            await interaction.followup.send("Destek talebi oluşturulurken bir hata oluştu.", ephemeral=True)

class CloseTicketView(ui.View):
    def __init__(self, ticket_bot_instance):
        super().__init__(timeout=None)
        self.bot = ticket_bot_instance

    @ui.button(label="Talebi Kapat", style=discord.ButtonStyle.red, custom_id="close_ticket_button", emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Destek talebi 5 saniye içinde kapatılacak...")

        user_id_to_remove = None
        for uid, cid in active_tickets.items():
            if cid == interaction.channel.id:
                user_id_to_remove = uid
                break

        if user_id_to_remove:
            del active_tickets[user_id_to_remove]

        await asyncio.sleep(5)
        await interaction.channel.delete(reason="Destek talebi kapatıldı.")


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

    @app_commands.command(name="ticketpanel", description="Destek talebi oluşturma panelini gönderir.")
    @app_commands.default_permissions(administrator=True)
    async def ticketpanel(self, interaction: discord.Interaction):
        panel_embed = create_embed(
            "Destek Merkezi",
            "Destek talebi oluşturmak için aşağıdaki butona tıklayın.",
            discord.Color.dark_blue()
        )
        await interaction.channel.send(embed=panel_embed, view=TicketView(self))
        await interaction.response.send_message("Destek paneli başarıyla oluşturuldu.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        guild = self.get_guild(int(os.getenv("GUILD_ID")))
        if not guild: return

        # DM'den kanala köprü
        if isinstance(message.channel, discord.DMChannel) and message.author.id in active_tickets:
            ticket_channel = guild.get_channel(active_tickets[message.author.id])
            if ticket_channel:
                dm_embed = create_embed("Kullanıcıdan Gelen Mesaj", message.content, discord.Color.green(), author=message.author)
                await ticket_channel.send(embed=dm_embed)

        # Kanaldan DM'e köprü
        elif message.channel.id in active_tickets.values():
            user_id = None
            for uid, cid in active_tickets.items():
                if cid == message.channel.id:
                    user_id = uid
                    break

            if user_id:
                user = guild.get_member(user_id)
                support_role_id = int(os.getenv("TICKET_SUPPORT_ROLE_ID"))
                author_roles = [role.id for role in message.author.roles]

                if user and support_role_id in author_roles:
                    reply_embed = create_embed("Destek Ekibinden Cevap", message.content, discord.Color.gold(), author=message.author)
                    try:
                        await user.send(embed=reply_embed)
                    except discord.Forbidden:
                        await message.channel.send("Kullanıcının DM'leri kapalı, mesaj gönderilemedi.", delete_after=10)
