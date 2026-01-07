import discord
from discord.ext import commands
import os
import logging
import traceback
from utils import create_embed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class BaseSentinel(commands.Bot):
    def __init__(self, command_prefix, intents, bot_name):
        super().__init__(command_prefix=command_prefix, intents=intents)
        self.bot_name = bot_name
        self.logger = logging.getLogger(self.bot_name)
        self.guild_id = discord.Object(id=os.getenv("GUILD_ID"))
        self.error_log_channel_id = os.getenv("ERROR_LOG_CHANNEL")
        self.error_log_channel = None

    async def on_ready(self):
        self.logger.info(f'{self.user} olarak giriş yapıldı. Sunucu ID: {self.guild_id.id}')
        if self.error_log_channel_id:
            try:
                self.error_log_channel = await self.fetch_channel(int(self.error_log_channel_id))
            except (discord.NotFound, ValueError):
                self.logger.warning(f"ERROR_LOG_CHANNEL ID '{self.error_log_channel_id}' geçersiz.")
        await self.tree.sync(guild=self.guild_id)

    async def log_error_to_channel(self, error_type: str, error: Exception, context: str = "N/A"):
        if not self.error_log_channel: return
        tb_text = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        if len(tb_text) > 1900: tb_text = "..." + tb_text[-1800:]
        error_description = f"**Tür:** `{error_type}`\n**Bağlam:** `{context}`\n**Hata:** `{error}`\n```python\n{tb_text}\n```"
        embed = create_embed(f"🚨 Bot Hatası: {self.bot_name}", error_description, discord.Color.dark_red())
        try:
            await self.error_log_channel.send(embed=embed)
        except Exception as e:
            self.logger.error(f"Hata log'u kanala gönderilemedi: {e}")

    async def on_error(self, event, *args, **kwargs):
        exc_info = traceback.sys.exc_info()
        self.logger.error(f'İşlenmemiş hata: {event}', exc_info=exc_info)
        await self.log_error_to_channel("Unhandled Event Error", exc_info[1], context=event)

    async def on_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        if isinstance(error, commands.CommandNotFound): return

        original_error = getattr(error, 'original', error)

        if isinstance(original_error, discord.Forbidden):
            error_message = "Bu işlemi gerçekleştirmek için yeterli yetkiye sahip değilim. Lütfen rol hiyerarşimi kontrol edin."
        else:
            self.logger.error(f'Komut "{interaction.data.get("name")}" hatası:', exc_info=original_error)
            context = f"Command: /{interaction.data.get('name')} by {interaction.user.name}"
            await self.log_error_to_channel("App Command Error", original_error, context=context)
            error_message = "Beklenmedik bir hata oluştu. Geliştiriciler bilgilendirildi."

        error_embed = create_embed("Komut Hatası", error_message, discord.Color.red())
        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
        except discord.NotFound:
             self.logger.warning("Etkileşim zaman aşımına uğradı.")

    async def start_bot(self, token_env_var):
        token = os.getenv(token_env_var)
        if not token:
            self.logger.critical(f'{token_env_var} bulunamadı!')
            return
        try:
            await self.start(token)
        except discord.LoginFailure:
            self.logger.critical(f'{self.bot_name} için geçersiz token.')
        except Exception as e:
            self.logger.critical(f'{self.bot_name} başlatılamadı: {e}', exc_info=True)
