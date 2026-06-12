import re
from fastapi import FastAPI, Response, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
from urllib.parse import urljoin, quote

app = FastAPI()

# Enable CORS for frontend player
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "KageWatch V2 Streaming Proxy is Live! 🚀"}

@app.get("/proxy")
def m3u8_proxy(url: str, referer: str = ""):
    try:
        # 1. Solid Fake Headers
        headers = {
            "Referer": referer,
            "Origin": referer.rstrip('/'), # Added Origin header
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        
        # 2. Use stream=True to prevent memory locks
        req = requests.get(url, headers=headers, stream=True)
        content_type = req.headers.get("content-type", "")
        
        # 3. If it's a playlist (.m3u8), we need to inject the proxy everywhere
        if ".m3u8" in url or "mpegurl" in content_type.lower() or "application/x-mpegurl" in content_type.lower():
            text = req.text
            new_content = ""
            
            for line in text.splitlines():
                if not line.strip():
                    continue
                
                # 🔴 FIX 1: Catch hidden URIs inside tags (like Encryption Keys or Audio Tracks)
                if line.startswith("#"):
                    # This regex replaces URI="something" with our proxy URL
                    line = re.sub(
                        r'URI="([^"]+)"', 
                        lambda m: f'URI="http://127.0.0.1:8000/proxy?url={quote(urljoin(url, m.group(1)))}&referer={quote(referer)}"', 
                        line
                    )
                    new_content += line + "\n"
                else:
                    # 🔴 FIX 2: Proxy the actual video chunk (.ts) lines
                    abs_url = urljoin(url, line)
                    proxy_link = f"https://kagewatch-proxy.onrender.com/proxy?url={quote(abs_url)}&referer={quote(referer)}"
                    new_content += proxy_link + "\n"
                    
            return Response(content=new_content, media_type="application/vnd.apple.mpegurl")
            
        # 4. If it's a video chunk (.ts) or key file, STREAM it instantly!
        else:
            # 🔴 FIX 3: StreamingResponse delivers video bytes to the player immediately
            return StreamingResponse(req.iter_content(chunk_size=1024*1024), media_type=content_type)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
