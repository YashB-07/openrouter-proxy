# OpenRouter Proxy

A FastAPI proxy that sits between a local client and [OpenRouter](https://openrouter.ai).

---

## Features

- **Proxy forwarding:**  accepts OpenAI-format requests, forwards to OpenRouter, returns OpenAI-format responses
- **System prompt injection:**  every request gets a system prompt prepended at the proxy layer, clients don't need to know about it
- **Tool calling:**  client defines tools locally, model decides when to call them, client executes and loops
- **Streaming:**  SSE streaming with live token output and tool call fragment reassembly

---

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file:

```
OPENROUTER_API_KEY=<your_key_here>
MODEL_NAME=<model to use>
```

---

## Running

Start the proxy server:

```bash
uvicorn main:app --reload
```

Start the CLI assistant:

```bash
# non-streaming (default)
python launch_assistant.py

# streaming
python launch_assistant.py --stream
```

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/chat/completions` | OpenAI-compatible Proxy endpoint |
| `GET` | `/health` | Health check |

Interactive API docs available at `http://localhost:8000/docs` once the server is running.

---

## Project Structure

```
main.py               # FastAPI proxy server
launch_assistant.py   # Interactive CLI chat client
tools.py              # Tool definitions and implementations
models.py             # Pydantic models (shared)
requirements.txt
```
