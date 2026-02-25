import asyncio
import asyncpg

async def test():
    conn = await asyncpg.connect(
        user="postgres",
        password="kolbasA@1977",
        database="vk_bmi_crm",
        host="127.0.0.1",
        port=5432,
        ssl=False
    )
    print("CONNECTED")
    await conn.close()

asyncio.run(test())