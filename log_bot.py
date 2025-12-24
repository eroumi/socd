import discord
from base_sentinel import BaseSentinel
import os
from utils import create_embed

class LogBot(BaseSentinel):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents, bot_name="LogBot")

    async def on_ready(self):
        await super().on_ready()
        self.mod_log_channel = self.get_channel(int(os.getenv("MOD_LOG_CHANNEL")))
        self.guard_log_channel = self.get_channel(int(os.getenv("GUARD_LOG_CHANNEL")))
        self.ticket_log_channel = self.get_channel(int(os.getenv("TICKET_LOG_CHANNEL")))
        self.error_log_channel = self.get_channel(int(os.getenv("ERROR_LOG_CHANNEL")))

    async def log_action(self, channel_type: str, embed: discord.Embed):
        """Belirtilen kanala log mesajı gönderir."""
        channel = getattr(self, f"{channel_type}_log_channel", None)
        if channel:
            await channel.send(embed=embed)
        else:
            self.logger.warning(f"{channel_type}_log_channel bulunamadı veya geçersiz.")
