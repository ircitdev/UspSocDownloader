#!/usr/bin/env python3
"""Check bot status"""
import asyncio
import aiohttp
import sys

async def check_bot():
    token = '8511650801:AAEGVXeNJeHHhl-ryB8qvQ0dTLTNse-IDK0'
    try:
        async with aiohttp.ClientSession() as session:
            # Check getMe
            async with session.get(f'https://api.telegram.org/bot{token}/getMe') as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print('✅ Бот активен на Telegram')
                    result = data.get('result', {})
                    print(f'   Бот: {result.get("first_name")} (@{result.get("username")})')
                    print(f'   ID: {result.get("id")}')
                    return True
                else:
                    print(f'❌ Ошибка: HTTP {resp.status}')
                    return False
    except Exception as e:
        print(f'❌ Ошибка подключения: {e}')
        return False

if __name__ == '__main__':
    result = asyncio.run(check_bot())
    sys.exit(0 if result else 1)
