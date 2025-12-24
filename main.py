import asyncio
import os
from dotenv import load_dotenv
import logging

load_dotenv()

from log_bot import LogBot
from guard_I import GuardI
from guard_II import GuardII
from guard_III import GuardIII
from system_bot import SystemBot
from ticket_bot import TicketBot
import database

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    logger.info("Discord Sentinel Network başlatılıyor...")
    log_bot = LogBot()
    bots = [
        (log_bot, "LOG_BOT_TOKEN"),
        (GuardI(log_bot), "GUARD_I_TOKEN"),
        (GuardII(log_bot), "GUARD_II_TOKEN"),
        (GuardIII(log_bot), "GUARD_III_TOKEN"),
        (SystemBot(log_bot), "SYSTEM_BOT_TOKEN"),
        (TicketBot(log_bot), "TICKET_BOT_TOKEN"),
    ]
    tasks = [bot.start_bot(token_name) for bot, token_name in bots]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    # İlk iş olarak veritabanını başlat
    database.initialize_database()

    required_vars = [
        "GUILD_ID", "WHITELIST_USERS", "LOG_BOT_TOKEN", "GUARD_I_TOKEN",
        "GUARD_II_TOKEN", "GUARD_III_TOKEN", "SYSTEM_BOT_TOKEN", "TICKET_BOT_TOKEN",
        "MOD_LOG_CHANNEL", "GUARD_LOG_CHANNEL"
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.critical(f"Eksik ortam değişkenleri: {', '.join(missing_vars)}")
        logger.critical("Lütfen .env dosyanızı .env.example'a göre doldurduğunuzdan emin olun.")
    else:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            logger.info("Kullanıcı tarafından kapatıldı. Discord Sentinel Network durduruluyor.")
        except Exception as e:
            logger.critical(f"Ana programda beklenmedik bir hata oluştu: {e}", exc_info=True)
