import discord
from discord.ext import commands
from base_sentinel import BaseSentinel
from utils import create_embed, send_dm_notification
import os
from collections import defaultdict, deque
import time
import database

class GuardII(BaseSentinel):
    def __init__(self, log_bot):
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents, bot_name="GuardII")
        self.log_bot = log_bot
        self.whitelist = [int(user_id) for user_id in os.getenv("WHITELIST_USERS", "").split(',') if user_id]
        self.forbidden_words = [word.strip().lower() for word in os.getenv("FORBIDDEN_WORDS", "").split(',') if word.strip()]
        self.spam_count = int(os.getenv("SPAM_MESSAGE_COUNT", 5))
        self.spam_seconds = int(os.getenv("SPAM_TIME_SECONDS", 5))
        self.user_messages = defaultdict(lambda: deque(maxlen=self.spam_count))

    async def punish_user(self, message: discord.Message, reason: str):
        user = message.author
        kick_reason = f"Guard II: {reason}"

        await send_dm_notification(user, message.guild.name, "Atılma", reason, self.user)

        try: await message.channel.purge(limit=100, check=lambda m: m.author == user)
        except discord.Forbidden: pass

        try:
            await message.guild.kick(user, reason=kick_reason)
            database.add_record("warnings", {"user_id": user.id, "moderator_id": self.user.id, "reason": f"(Otomatik Kick) {kick_reason}", "timestamp": int(time.time())})
            log_embed = create_embed("Guard II - Sohbet İhlali", f"{user.mention} {reason} sebebiyle atıldı.", discord.Color.red(), author=user)
            await self.log_bot.log_action("guard", log_embed)
        except discord.Forbidden:
            self.logger.error(f"{user.name} atılamadı.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild or message.author.id in self.whitelist: return

        if any(word in message.content.lower() for word in self.forbidden_words):
            await self.punish_user(message, "Yasaklı kelime kullanımı.")
            return

        now = time.time()
        self.user_messages[message.author.id].append(now)
        timestamps = self.user_messages[message.author.id]
        if len(timestamps) == self.spam_count and timestamps[-1] - timestamps[0] <= self.spam_seconds:
            await self.punish_user(message, "Spam (hızlı mesaj).")
            if message.author.id in self.user_messages: del self.user_messages[message.author.id]
