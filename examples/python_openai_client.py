from __future__ import annotations

import os

from openai import OpenAI


def main() -> None:
    base_url = os.getenv("CONEXUS_BASE_URL", "http://localhost:8000/v1")
    api_key = os.environ["CONEXUS_API_KEY"]  # project key: cx_live_...
    model = os.getenv("CONEXUS_MODEL", "gpt-4o-mini")

    client = OpenAI(base_url=base_url, api_key=api_key)

    print("== non-streaming ==")
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Say hello from Conexus."}],
        temperature=0.2,
        max_tokens=64,
    )
    print(resp.choices[0].message.content)

    print("\n== streaming ==")
    stream = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Stream three short words."}],
        temperature=0.2,
        max_tokens=32,
        stream=True,
    )
    for event in stream:
        delta = event.choices[0].delta
        if delta and delta.content:
            print(delta.content, end="", flush=True)
    print()


if __name__ == "__main__":
    main()

