# core.py
import os
import asyncio
import time
import json
import sys
from telethon import TelegramClient, functions, types, errors
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator
from config import API_ID, API_HASH, SESSION_FOLDER, GROUPS_FILE, PROXY_FILE, TIMING_FILE

# Отключаем предупреждения debugger
os.environ['PYDEVD_DISABLE_FILE_VALIDATION'] = '1'

# Глобальные переменные
last_post_ids = {}
LAST_POSTS_FILE = 'last_posts.json'

def clear_sqlite_locks(session_path):
    """Очистка временных файлов блокировок"""
    for ext in ['-wal', '-shm', '-journal']:
        lock_file = f"{session_path}{ext}"
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
            except:
                pass

def read_groups():
    """Чтение списка групп с валидацией"""
    if not os.path.exists(GROUPS_FILE):
        raise ValueError(f"Файл {GROUPS_FILE} не найден")
    
    with open(GROUPS_FILE, 'r', encoding='utf-8') as f:
        groups = [line.strip() for line in f if line.strip()]
        if not groups:
            raise ValueError("Файл групп пуст")
        return groups

def save_last_posts():
    """Сохранение ID сообщений"""
    try:
        with open(LAST_POSTS_FILE, 'w') as f:
            json.dump(last_post_ids, f)
    except Exception as e:
        print(f"⚠️ Ошибка сохранения last_posts: {e}")

def load_last_posts():
    """Загрузка ID сообщений"""
    global last_post_ids
    if os.path.exists(LAST_POSTS_FILE):
        try:
            with open(LAST_POSTS_FILE, 'r') as f:
                last_post_ids = json.load(f)
        except:
            last_post_ids = {}

async def check_admin_rights(client, group_entity):
    """Проверка прав администратора"""
    try:
        participant = await client(functions.channels.GetParticipantRequest(
            channel=await client.get_input_entity(group_entity),
            participant=await client.get_me()
        ))
        return isinstance(participant.participant, 
                        (ChannelParticipantAdmin, ChannelParticipantCreator))
    except Exception as e:
        print(f"⚠️ Ошибка проверки прав: {e}")
        return False

async def repost_last_post(client, channel_entity, groups):
    """Репост последнего сообщения"""
    global last_post_ids
    last_post_ids.clear()

    try:
        message = await client.get_messages(channel_entity, limit=1)
        if not message:
            print("❌ В канале нет сообщений")
            return False

        print(f"🔄 Репост сообщения ID {message[0].id}...")
        for group_str in groups:
            try:
                group = await client.get_input_entity(group_str)
                result = await client.forward_messages(
                    entity=group,
                    messages=message,
                    drop_author=True,
                    silent=True
                )
                
                if result:
                    last_post_ids[group_str] = result[0].id
                    print(f"✅ Успешно в {group_str}")
                await asyncio.sleep(2)
            except Exception as e:
                print(f"⚠️ Ошибка в {group_str}: {e}")

        save_last_posts()
        return True
    except Exception as e:
        print(f"🔥 Ошибка репоста: {e}")
        return False

async def process_group_action(client, action, group_str, msg_id):
    """Обработка действий с сообщениями"""
    try:
        group = await client.get_input_entity(group_str)
        
        if action == "pin":
            await client.pin_message(group, msg_id)
            print(f"📌 Закреплено в {group_str}")
        elif action == "unpin":
            await client.unpin_message(group, msg_id)
            print(f"📎 Откреплено в {group_str}")
        elif action == "delete":
            await client.delete_messages(group, [msg_id])
            print(f"🗑 Удалено в {group_str}")
    except Exception as e:
        print(f"⚠️ Ошибка {action} в {group_str}: {e}")

async def main_loop(channel_username, command):
    """Основной цикл выполнения"""
    try:
        load_last_posts()
        
        if not os.path.exists(SESSION_FOLDER):
            os.makedirs(SESSION_FOLDER)

        session_files = [f for f in os.listdir(SESSION_FOLDER) 
                      if f.endswith('.session') and not f.startswith('.')]
        if not session_files:
            print("❌ Нет валидных файлов сессий")
            return

        groups = read_groups()
        
        for session_file in session_files:
            session_path = os.path.join(SESSION_FOLDER, session_file)
            clear_sqlite_locks(session_path)

            # Используем стандартную сессию вместо кастомной
            client = TelegramClient(
                session=session_path,
                api_id=API_ID,
                api_hash=API_HASH,
                system_version="4.16.30-vxCustom",
                request_retries=3,
                retry_delay=1
            )
            
            try:
                await client.start()
                print(f"\n🟢 Сессия {session_file} запущена")
                entity = await client.get_entity(channel_username)

                if command == "/repost_all":
                    await asyncio.sleep(read_timing() * 60)
                    await repost_last_post(client, entity, groups)
                
                elif command in ["/pin_last", "/unpin_last", "/delete_last"]:
                    action = {
                        "/pin_last": "pin",
                        "/unpin_last": "unpin",
                        "/delete_last": "delete"
                    }[command]

                    for group_str, msg_id in last_post_ids.items():
                        await process_group_action(client, action, group_str, msg_id)
                    
                    if command == "/delete_last":
                        last_post_ids.clear()
                        if os.path.exists(LAST_POSTS_FILE):
                            os.remove(LAST_POSTS_FILE)

            except Exception as e:
                print(f"🔥 Ошибка в сессии {session_file}: {e}")
            finally:
                await client.disconnect()
                print(f"🔵 Сессия {session_file} остановлена")

    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Использование: python core.py @channel_username /command")
        sys.exit(1)

    asyncio.run(main_loop(sys.argv[1], sys.argv[2]))