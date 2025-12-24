import discord
from discord.ext import commands
from base_sentinel import BaseSentinel
from utils import create_embed
import os
from collections import defaultdict, deque
import time

class GuardII(BaseSentinel):
    def __init__(self, log_bot):
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True  # Mesaj içeriğini okumak için gerekli
        super().__init__(command_prefix="!", intents=intents, bot_name="GuardII")
        self.log_bot = log_bot

        # .env'den ayarları yükle
        self.whitelist = [int(user_id) for user_id in os.getenv("WHITELIST_USERS", "").split(',') if user_id]
        self.forbidden_words = [word.strip().lower() for word in os.getenv("FORBIDDEN_WORDS", "").split(',') if word.strip()]
        self.spam_message_count = int(os.getenv("SPAM_MESSAGE_COUNT", 5))
        self.spam_time_seconds = int(os.getenv("SPAM_TIME_SECONDS", 5))

        # Kullanıcıların mesaj zaman damgalarını saklamak için
        self.user_messages = defaultdict(lambda: deque(maxlen=self.spam_message_count))
        self.logger.info(f"Forbidden words loaded: {self.forbidden_words}")

    async def punish_user(self, message: discord.Message, reason: str):
        """Kullanıcıyı cezalandırır: Kick + Mesajları Temizle + Logla"""
        user = message.author
        channel = message.channel

        # Loglama
        log_description = (
            f"**Kullanıcı:** {user.mention} (`{user.id}`)\n"
            f"**Kanal:** {channel.mention}\n"
            f"**Sebep:** {reason}"
        )
        log_embed = create_embed(
            title="Guard II - Sohbet İhlali Tespit Edildi",
            description=log_description,
            color=discord.Color.red(),
            author=user
        )
        await self.log_bot.log_action("guard", log_embed)

        # Mesajları Temizle
        try:
            await channel.purge(limit=100, check=lambda m: m.author == user)
        except discord.Forbidden:
            self.logger.error(f"{channel.name} kanalında {user.name} adlı kullanıcının mesajları silinemedi, yetkim yetersiz.")
        except Exception as e:
            self.logger.error(f"Mesajları silerken bir hata oluştu: {e}", exc_info=True)

        # Kick
        try:
            await message.guild.kick(user, reason=f"Guard II: {reason}")
        except discord.Forbidden:
            self.logger.error(f"{user.name} atılamadı, yetkim yetersiz.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Botları, DM'leri ve beyaz listedeki kullanıcıları yoksay
        if message.author.bot or not message.guild or message.author.id in self.whitelist:
            return

        # --- Yasaklı Kelime Kontrolü ---
        message_content_lower = message.content.lower()
        if any(word in message_content_lower for word in self.forbidden_words):
            await self.punish_user(message, "Yasaklı kelime kullanımı.")
            return

        # --- Spam Kontrolü ---
        current_time = time.time()
        self.user_messages[message.author.id].append(current_time)

        # Sadece son N mesajın zaman damgalarını kontrol et
        timestamps = self.user_messages[message.author.id]
        if len(timestamps) == self.spam_message_count:
            # İlk ve son mesaj arasındaki zaman farkını kontrol et
            if timestamps[-1] - timestamps[0] <= self.spam_time_seconds:
                await self.punish_user(message, "Spam (hızlı mesaj gönderme).")
                # İhlal sonrası kullanıcı mesajlarını temizle
                if message.author.id in self.user_messages:
                    del self.user_messages[message.author.id]
                return
