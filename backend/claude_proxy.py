from fastapi import FastAPI, Request, Response
import httpx

app = FastAPI()

ANTHROPIC_URL = "https://api.anthropic.com"

@app.get("/")
def health():
    return {"ok": True, "service": "local-claude-proxy"}

@app.post("/{path:path}")
async def proxy(path: str, request: Request):
    body = await request.body()

    headers = {
        "content-type": "application/json",
        "x-api-key": request.headers.get("x-api-key", ""),
        "anthropic-version": request.headers.get("anthropic-version", "2023-06-01"),
    }

    async with httpx.AsyncClient(timeout=90) as client:
        r = await client.post(
            f"{ANTHROPIC_URL}/{path}",
            headers=headers,
            content=body
        )

    return Response(
        content=r.content,
        status_code=r.status_code,
        media_type="application/json"
    )
