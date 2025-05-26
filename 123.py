from telethon.sync import TelegramClient

client = TelegramClient('/home/loluto/Desktop/WORK/TG/sessions/', '21791234', '0f41fec19918635179266eb3156b11a2')
client.start()

try:
    client.send_message(-1002537861015, "Тестовое сообщение")
    print("Сообщение отправлено!")
except Exception as e:
    print(f"Ошибка: {e}")