import os
import argparse
import httpx
import json
from typing import Optional
from dotenv import load_dotenv

from models import Message
from tools import tools, run_tool

CYAN  = "\033[36m"
RESET = "\033[0m"
SEP   = f"{CYAN}{'─' * 52}{RESET}"

load_dotenv()
PROXY_URL = "http://localhost:8000/v1/chat/completions"
MODEL = os.environ["MODEL_NAME"]


def _iter_sse_lines(response: httpx.Response):
    """Parse SSE lines from a streaming response, yield each as a parsed dict."""
    for raw_line in response.iter_lines():
        line = raw_line.strip()
        if not line or not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if payload == "[DONE]":
            break
        try:
            yield json.loads(payload)
        except json.JSONDecodeError:
            continue


def chat(messages: list[Message], stream: bool = False) -> Optional[str]:
    request_body = {
        "model": MODEL,
        "messages": [m.model_dump(exclude_none=True) for m in messages],
        "tools": [t.model_dump() for t in tools],
    }

    while True:
        if not stream:
            response = httpx.post(PROXY_URL, json=request_body, timeout=60)

            if not response.is_success:
                print(f"[error] {response.status_code}: {response.text}")
                return None

            data = response.json()
            choice = data["choices"][0]
            finish_reason = choice["finish_reason"]
            assistant_msg = choice["message"]

            messages.append(Message(**assistant_msg))

            if finish_reason == "tool_calls":
                print(f"\n{SEP}")
                for tool_call in assistant_msg["tool_calls"]:
                    name = tool_call["function"]["name"]
                    args = tool_call["function"]["arguments"]
                    print(f"{CYAN}  [tool called]  {name}({args}){RESET}")
                    result = run_tool(name, args)
                    print(f"{CYAN}  [tool response]  {result}{RESET}")
                    messages.append(Message(
                        role="tool",
                        tool_call_id=tool_call["id"],
                        content=result,
                    ))
                print(f"{SEP}\n")
                request_body["messages"] = [m.model_dump(exclude_none=True) for m in messages]

            elif finish_reason == "stop":
                return assistant_msg["content"]

        else:
            request_body["stream"] = True

            tokens = []
            tool_call_fragments = {}
            finish_reason = None

            print("\nAssistant: ", end="", flush=True)

            with httpx.stream("POST", PROXY_URL, json=request_body, timeout=60) as response:
                if not response.is_success:
                    response.read()
                    print(f"\n[error] {response.status_code}: {response.text}")
                    return None

                for chunk in _iter_sse_lines(response):
                    choice = chunk.get("choices", [{}])[0]
                    finish_reason = choice.get("finish_reason") or finish_reason
                    delta = choice.get("delta", {})

                    token = delta.get("content")
                    if token:
                        print(token, end="", flush=True)
                        tokens.append(token)

                    # accumulate tool call fragments
                    for tc_delta in delta.get("tool_calls") or []:
                        idx = tc_delta["index"]
                        if idx not in tool_call_fragments:
                            tool_call_fragments[idx] = {
                                "id": tc_delta.get("id", ""),
                                "type": "function",
                                "function": {"name": "", "arguments": ""}
                            }
                        fn = tc_delta.get("function") or {}
                        if fn.get("name"):
                            tool_call_fragments[idx]["function"]["name"] += fn["name"]
                        if fn.get("arguments"):
                            tool_call_fragments[idx]["function"]["arguments"] += fn["arguments"]

            # stream done, now decide what to do based on finish_reason
            if finish_reason == "tool_calls" or tool_call_fragments:
                assembled = [tool_call_fragments[i] for i in sorted(tool_call_fragments)]
                messages.append(Message(role="assistant", content=None, tool_calls=assembled))

                print(f"\n{SEP}")
                for tool_call in assembled:
                    name = tool_call["function"]["name"]
                    args = tool_call["function"]["arguments"]
                    print(f"{CYAN}  tool called   → {name}({args}){RESET}")
                    result = run_tool(name, args)
                    print(f"{CYAN}  tool returned → {result}{RESET}")
                    messages.append(Message(
                        role="tool",
                        tool_call_id=tool_call["id"],
                        content=result,
                    ))
                print(SEP)

                request_body["messages"] = [m.model_dump(exclude_none=True) for m in messages]

            elif finish_reason == "stop" or tokens:
                # if model skip finish_reason="stop", treat any accumulated content as done
                full_content = "".join(tokens)
                messages.append(Message(role="assistant", content=full_content))
                return full_content

            else:
                return None


def main(stream: bool = False):
    mode = "streaming" if stream else "non-streaming"
    print(f"Assistant ready [{mode}]. Type 'quit' to exit.\n")
    history: list[Message] = []

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            break

        history.append(Message(role="user", content=user_input))
        reply = chat(history, stream=stream)
        if reply is None:
            break
        if not stream:
            print(f"\nAssistant: {reply}\n")
        else:
            print("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stream", dest="stream", action="store_true", default=False)
    parser.add_argument("--no-stream", dest="stream", action="store_false")
    args = parser.parse_args()
    main(stream=args.stream)
