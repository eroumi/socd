import discord
from datetime import datetime

def create_embed(title: str, description: str, color: discord.Color, author: discord.User = None, footer_text: str = None) -> discord.Embed:
    """
    Standartlaştırılmış bir Discord Embed nesnesi oluşturur.

    Args:
        title (str): Embed başlığı.
        description (str): Embed açıklaması.
        color (discord.Color): Embed rengi.
        author (discord.User, optional): Embed'i tetikleyen kullanıcı. Defaults to None.
        footer_text (str, optional): Alt bilgi metni. Defaults to None.

    Returns:
        discord.Embed: Oluşturulan Embed nesnesi.
    """
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
