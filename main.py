import os
import time
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import httpx

from models import Message, ChatRequest

logging.basicConfig(level=logging.INFO, format="[%(levelname)s]:     %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

SYSTEM_PROMPT = """
    You are a helpful general-purpose assistant. "
    Always respond in Hindi using English letters (Hinglish). Do not use Devanagari script.
"""

app = FastAPI(title="OpenRouter Proxy")


def inject_system_prompt(messages: list[Message]) -> list[Message]:
    system_message = Message(role="system", content=SYSTEM_PROMPT.strip())
    return [system_message] + messages


async def _stream_openrouter(body: dict, headers: dict):
    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream(
            "POST",
            f"{OPENROUTER_BASE_URL}/chat/completions",
            json=body,
            headers=headers,
        ) as resp:
            if resp.status_code != 200:
                error = await resp.aread()
                yield f"data: {error.decode()}\n\n".encode()
                return
            async for chunk in resp.aiter_bytes():
                if chunk:
                    yield chunk


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    start = time.time()
    request.messages = inject_system_prompt(request.messages)
    body = request.model_dump(exclude_none=True)

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
    }

    if request.stream:
        logger.info(f"POST /v1/chat/completions | model={request.model} | stream=True")
        return StreamingResponse(
            _stream_openrouter(body, headers),
            media_type="text/event-stream",
        )

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            json=body,
            headers=headers,
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    data = resp.json()
    usage = data.get("usage", {})
    latency = round((time.time() - start) * 1000)
    logger.info(
        f"POST /v1/chat/completions | model={request.model} | stream=False"
        f" | {latency}ms | prompt={usage.get('prompt_tokens')} completion={usage.get('completion_tokens')}"
    )
    return JSONResponse(content=data)


@app.get("/health")
async def health():
    return {"status": "ok"}
