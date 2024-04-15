import io
import aiohttp

async def download_file(url) -> io.BytesIO | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            data = io.BytesIO(await resp.read())
            return data
