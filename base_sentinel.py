import discord
from discord.ext import commands
import os
import logging

# Logging'i ayarla
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class BaseSentinel(commands.Bot):
    """
    Tüm Sentinel botları için temel sınıf.
    Ortak olayları, hata yönetimini ve yapılandırmayı yönetir.
    """
    def __init__(self, command_prefix, intents, bot_name):
        super().__init__(command_prefix=command_prefix, intents=intents)
        self.bot_name = bot_name
        self.logger = logging.getLogger(self.bot_name)
        self.guild_id = discord.Object(id=os.getenv("GUILD_ID"))

    async def on_ready(self):
        """Bot hazır olduğunda çağrılır."""
        self.logger.info(f'{self.user} olarak giriş yapıldı. Sunucu ID: {self.guild_id.id}')
        # Komutları sadece belirtilen sunucu için senkronize et
        await self.tree.sync(guild=self.guild_id)
        self.logger.info(f'Komut ağacı {self.guild_id.id} sunucusu için senkronize edildi.')

    async def on_error(self, event, *args, **kwargs):
        """Beklenmedik bir hata oluştuğunda tetiklenir."""
        self.logger.error(f'İşlenmemiş bir hata oluştu: {event}', exc_info=True)
        # Gerekirse hata log kanalına gönderim yapılabilir.

    async def on_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        """Bir uygulama komutunda hata oluştuğunda tetiklenir."""
        if isinstance(error, commands.CommandNotFound):
            return  # Bilinmeyen komutları sessizce yoksay

        self.logger.error(f'Komut "{interaction.data.get("name", "Bilinmiyor")}" sırasında bir hata oluştu:', exc_info=error)

        error_embed = discord.Embed(
            title="Komut Hatası",
            description=f"Komutu işlerken bir hata oluştu. Lütfen daha sonra tekrar deneyin.",
            color=discord.Color.red()
        )

        if interaction.response.is_done():
            await interaction.followup.send(embed=error_embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=error_embed, ephemeral=True)

    async def start_bot(self, token_env_var):
        """Botu ilgili token ile başlatır."""
        token = os.getenv(token_env_var)
        if not token:
            self.logger.critical(f'{token_env_var} ortam değişkeni bulunamadı!')
            return

        try:
            await self.start(token)
        except discord.LoginFailure:
            self.logger.critical(f'{self.bot_name} için geçersiz token. Lütfen {token_env_var} değişkenini kontrol edin.')
        except Exception as e:
            self.logger.critical(f'{self.bot_name} başlatılırken kritik bir hata oluştu: {e}', exc_info=True)
