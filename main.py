import re
from fastapi import FastAPI, Response, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
from urllib.parse import urljoin, quote

app = FastAPI()

PROXY_BASE = "https://kagewatch-proxy.onrender.com/proxy"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "KageWatch Proxy Live 🚀"}

@app.get("/proxy")
def m3u8_proxy(url: str, referer: str = ""):
    headers = {
        "Referer": referer,
        "Origin": referer.rstrip("/"),
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
    }

    try:
        req = requests.get(url, headers=headers, stream=True, timeout=15)  # ✅ timeout add kiya
        content_type = req.headers.get("Content-Type", "")

        is_m3u8 = "m3u8" in url.lower() or "mpegurl" in content_type.lower()

        if is_m3u8:
            text = req.text
            new_lines = []

            for line in text.splitlines():
                stripped = line.strip()

                if not stripped:
                    new_lines.append(line)
                    continue

                if stripped.startswith("#"):
                    # ✅ URI="..." ke andar keys/audio tracks proxy karo
                    line = re.sub(
                        r'URI="([^"]+)"',
                        lambda m: (
                            f'URI="{PROXY_BASE}'
                            f'?url={quote(urljoin(url, m.group(1)))}'
                            f'&referer={quote(referer)}"'
                        ),
                        line,
                    )
                    new_lines.append(line)
                else:
                    # ✅ Relative aur absolute dono .ts / .m3u8 segments proxy karo
                    abs_url = urljoin(url, stripped)
                    proxy_url = f"{PROXY_BASE}?url={quote(abs_url)}&referer={quote(referer)}"
                    new_lines.append(proxy_url)

            return Response(
                content="\n".join(new_lines),
                media_type="application/vnd.apple.mpegurl",
            )

        # ✅ .ts chunks / key files stream karo
        return StreamingResponse(
            req.iter_content(chunk_size=1024 * 512),
            media_type=content_type or "application/octet-stream",
        )

    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Upstream request timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
