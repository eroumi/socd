import asyncio
import os
import discord
from dotenv import load_dotenv

# .env dosyasındaki ortam değişkenlerini yükle
load_dotenv()

# Gerekli Discord izinlerini (Intents) ayarla
# Botların durumunu değiştirebilmesi için temel izinler yeterlidir.
intents = discord.Intents.default()

# Botları başlatmak için asenkron bir fonksiyon
async def start_bot(token, bot_name):
    """
    Belirtilen token ile bir bot istemcisi oluşturur, başlatır ve durumunu ayarlar.
    """
    if not token:
        print(f"{bot_name} için token bulunamadı. Lütfen .env dosyasını kontrol edin.")
        return

    # Bot istemcisini oluştur
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        """
        Bot başarıyla Discord'a bağlandığında çalışır.
        """
        print(f'{client.user} olarak giriş yapıldı.')
        try:
            # Botun durumunu "Rahatsız Etmeyin" ve "Viltrum Network oynuyor" olarak ayarla
            game = discord.Game(name="Viltrum Network")
            await client.change_presence(status=discord.Status.dnd, activity=game)
            print(f'{client.user} durumu "Viltrum Network oynuyor" olarak ayarlandı.')
        except Exception as e:
            print(f"Durum değiştirilirken bir hata oluştu: {e}")

    try:
        # Botu başlat
        await client.start(token)
    except discord.errors.LoginFailure:
        print(f"HATA: {bot_name} için sağlanan token geçersiz.")
    except Exception as e:
        print(f"{bot_name} başlatılırken bir hata oluştu: {e}")

# Ana asenkron fonksiyon
async def main():
    """
    Tüm botları eş zamanlı olarak çalıştırmak için görevler oluşturur.
    """
    # .env dosyasından token'ları al
    tokens = [os.getenv(f"BOT_TOKEN_{i+1}") for i in range(6)]

    # Her bot için asenkron görevler oluştur
    tasks = []
    for i, token in enumerate(tokens):
        bot_name = f"Bot {i+1}"
        if token:
            # Her botu kendi görevi içinde başlat
            task = asyncio.create_task(start_bot(token, bot_name))
            tasks.append(task)
        else:
            print(f"BOT_TOKEN_{i+1} bulunamadı, bu bot atlanıyor.")

    # Tüm bot görevlerinin tamamlanmasını bekle
    if tasks:
        await asyncio.gather(*tasks)
    else:
        print("Çalıştırılacak hiçbir bot token'ı bulunamadı. Lütfen .env dosyanızı doldurun.")

# Betik doğrudan çalıştırıldığında ana fonksiyonu çağır
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram sonlandırılıyor.")
