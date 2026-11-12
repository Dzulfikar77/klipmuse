"""Probe minimal TikTokApi: buat sesi (tanpa ms_token) lalu ambil info 1 video dikenal.
Hasil apa pun dicatat apa adanya — probe ini mengukur apakah sesi anonim dari IP VM
diterima TikTok, BUKAN menguji library-nya."""
import asyncio
import json
import os
from urllib.parse import urlparse

from TikTokApi import TikTokApi

VIDEO_ID = "7703227788160961806"  # @leehoustonx fancy cafe (sudah dikenal proyek ini)


def egress_proxy() -> dict | None:
    """Proxy egress runtime dari env — Chromium tidak membacanya sendiri,
    jadi harus diserahkan eksplisit ke Playwright."""
    raw = next(
        (os.environ[k] for k in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy") if os.environ.get(k)),
        None,
    )
    if not raw:
        return None
    u = urlparse(raw)
    proxy: dict = {"server": f"{u.scheme}://{u.hostname}:{u.port}"}
    if u.username:
        proxy["username"] = u.username
    if u.password:
        proxy["password"] = u.password
    return proxy


async def main() -> None:
    proxy = egress_proxy()
    async with TikTokApi() as api:
        await api.create_sessions(
            num_sessions=1,
            sleep_after=3,
            headless=True,
            proxies=[proxy] if proxy else None,
        )
        video = api.video(id=VIDEO_ID)
        info = await video.info()
        stats = info.get("stats") or info.get("statsV2") or {}
        author = (info.get("author") or {}).get("uniqueId")
        print(json.dumps({"ok": True, "author": author, "stats": stats}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
