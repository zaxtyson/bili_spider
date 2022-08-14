import aiofiles


async def record_failed_mid(mid: int):
    async with aiofiles.open("logs/failed_mid", "a+") as f:
        f.writelines([str(mid)])
        