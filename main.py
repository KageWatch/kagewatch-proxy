from fastapi import FastAPI, Response, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import re
from urllib.parse import urljoin, quote

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/proxy")
def m3u8_proxy(url: str, referer: str = ""):
    headers = {
        "Referer": referer,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    try:
        req = requests.get(url, headers=headers, stream=True)
        
        # Agar ye .m3u8 file hai
        if "m3u8" in url or "application/x-mpegurl" in req.headers.get("Content-Type", ""):
            content = req.text
            # Chunks aur Keys ko absolute path mein convert karo
            def replace_path(match):
                full_url = urljoin(url, match.group(1))
                return f'"{full_url}"' if 'URI' in match.group(0) else f"https://kagewatch-proxy.onrender.com/proxy?url={quote(full_url)}&referer={quote(referer)}"
            
            # Regex for .ts files and keys
            content = re.sub(r'(https?://[^\s"\'\)]+\.ts)', lambda m: f"https://kagewatch-proxy.onrender.com/proxy?url={quote(m.group(1))}&referer={quote(referer)}", content)
            content = re.sub(r'URI="([^"]+)"', lambda m: f'URI="https://kagewatch-proxy.onrender.com/proxy?url={quote(urljoin(url, m.group(1)))}&referer={quote(referer)}"', content)
            
            return Response(content=content, media_type="application/vnd.apple.mpegurl")
        
        # Agar ye video chunk (.ts) hai
        return StreamingResponse(req.iter_content(chunk_size=1024*64), media_type=req.headers.get("Content-Type"))
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
