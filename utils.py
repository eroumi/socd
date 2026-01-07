import discord
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def create_embed(title: str, description: str, color: discord.Color, author: discord.User = None, footer_text: str = None) -> discord.Embed:
    """Standartlaştırılmış bir Discord Embed nesnesi oluşturur."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.utcnow()
    )
    if author:
        embed.set_author(name=author.display_name, icon_url=author.avatar.url if author.avatar else author.default_avatar.url)
    if footer_text:
        embed.set_footer(text=footer_text)
    else:
        embed.set_footer(text="Discord Sentinel Network")
    return embed

async def send_dm_notification(member: discord.Member, guild_name: str, action_type: str, reason: str, moderator: discord.User):
    """Kullanıcıya moderasyon eylemini bildiren bir DM gönderir."""
    color_map = {
        "Uyarı": discord.Color.yellow(),
        "Uyarı Kaldırıldı": discord.Color.light_grey(),
        "Atılma": discord.Color.orange(),
        "Yasaklanma": discord.Color.red(),
        "Susturulma": discord.Color.dark_grey(),
        "Susturma Kaldırıldı": discord.Color.blue(),
    }

    title = f"`{guild_name}` Sunucusunda Bir İşlem Yapıldı"
    description = (
        f"**İşlem:** {action_type}\n"
        f"**Sebep:** {reason}\n"
        f"**Yetkili:** {moderator.mention}"
    )

    embed = create_embed(title, description, color_map.get(action_type, discord.Color.default()), author=moderator)

    try:
        await member.send(embed=embed)
    except discord.Forbidden:
        logger.warning(f"Kullanıcı {member.name} ({member.id}) DM'leri kapalı olduğu için bildirim gönderilemedi.")
    except Exception as e:
        logger.error(f"Kullanıcıya DM gönderilirken beklenmedik bir hata oluştu: {e}", exc_info=True)
