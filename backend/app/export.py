# filename: export.py
import os
import json
import asyncio
from datetime import datetime, UTC
from app.db import get_qdrant_client, get_all_chats
from app.config import settings

async def export_chats(export_dir=settings.EXPORT_DIR, iso_format=True):
    print('Exporting chats to JSON')
    file_path = os.path.join(export_dir, 'chats.json')
    client = get_qdrant_client()
    chats = await get_all_chats(client)
    if iso_format:
        for chat in chats:
            chat['created'] = datetime.fromtimestamp(chat['created'], tz=UTC).isoformat()
            for message in chat['messages']:
                message['created'] = datetime.fromtimestamp(message['created'], tz=UTC).isoformat()
    with open(file_path, 'w') as file:
        json.dump(chats, file, indent=2)
    print(f'{len(chats)} chats exported')

def main():
    asyncio.run(export_chats())

if __name__ == '__main__':
    main()