import io
import aiohttp


MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024


async def download_file(url: str) -> io.BytesIO | None:
    timeout = aiohttp.ClientTimeout(total=30)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                data = io.BytesIO()
                async for chunk in resp.content.iter_chunked(64 * 1024):
                    data.write(chunk)
                    if data.tell() > MAX_DOWNLOAD_BYTES:
                        return None
                data.seek(0)
                return data
    except (aiohttp.ClientError, TimeoutError):
        return None
