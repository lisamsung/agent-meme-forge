"""Provider-agnostic image-generation client (OpenAI-compatible Images API).

Design rule: the generation endpoint is CONFIGURATION, not code. Point
``base_url`` / ``api_key`` / ``model`` at any OpenAI-compatible images endpoint
(a JMR/jmrai proxy today, OpenAI official, or a self-hosted gateway) without
touching any caller. The dense-frames recipe and the local assembly pipeline
stay provider-independent; only this thin adapter knows about a concrete endpoint.

Zero third-party dependencies (Python stdlib ``urllib`` only) so the same module
is reusable from the CLI, a Codex/Hermes skill run, or a future web backend.
No secrets are baked in — credentials come from args or environment.
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Sequence

DEFAULT_MODEL = "gpt-image-2"
DEFAULT_SIZE = "1024x1024"
DEFAULT_TIMEOUT = 300


class ImageProviderConfig:
    """Where to send image requests. The only place a concrete endpoint lives.

    Plain class (not a dataclass) so it loads the same way no matter how the module
    is imported (normal import, ``python file.py``, or importlib without sys.modules).
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str = DEFAULT_MODEL,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    @classmethod
    def from_env(
        cls,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> "ImageProviderConfig":
        """Resolve config from explicit args, then project env, then OPENAI_* fallbacks.

        base_url must include the API version path (e.g. https://host/v1); OpenAI
        official is https://api.openai.com/v1.
        """
        resolved_base = base_url or os.getenv("MEME_IMAGE_BASE_URL") or os.getenv("OPENAI_BASE_URL")
        resolved_key = api_key or os.getenv("MEME_IMAGE_API_KEY") or os.getenv("OPENAI_API_KEY")
        resolved_model = model or os.getenv("MEME_IMAGE_MODEL") or os.getenv("OPENAI_MODEL") or DEFAULT_MODEL
        if not resolved_base or not resolved_key:
            raise ValueError(
                "image provider needs base_url + api_key; set MEME_IMAGE_BASE_URL and "
                "MEME_IMAGE_API_KEY (or OPENAI_BASE_URL / OPENAI_API_KEY), or pass them explicitly."
            )
        return cls(base_url=resolved_base.rstrip("/"), api_key=resolved_key, model=resolved_model)


def _redact(text: str, secret: str) -> str:
    return text.replace(secret, "***") if secret else text


def _post(config: ImageProviderConfig, path: str, data: bytes, content_type: str) -> dict:
    request = urllib.request.Request(
        f"{config.base_url}{path}",
        data=data,
        headers={"Authorization": f"Bearer {config.api_key}", "Content-Type": content_type},
    )
    try:
        with urllib.request.urlopen(request, timeout=config.timeout) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:  # surface the API's error body, not a bare 400
        body = _redact(error.read().decode("utf-8", "replace")[:500], config.api_key)
        raise RuntimeError(f"image API {path} failed: HTTP {error.code} {body}") from error
    except urllib.error.URLError as error:  # DNS / connection refused / timeout / TLS
        raise RuntimeError(f"image API {path} unreachable at {config.base_url}: {error.reason}") from error
    try:
        return json.loads(payload)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"image API {path} returned non-JSON: {_redact(payload[:300], config.api_key)}") from error


def _save_first_image(response: dict, out_path: str | Path) -> Path:
    items = response.get("data") or []
    if not items:
        raise RuntimeError(f"image API returned no data: {json.dumps(response)[:300]}")
    item = items[0]
    if item.get("b64_json"):
        raw = base64.b64decode(item["b64_json"])
    elif item.get("url"):
        with urllib.request.urlopen(item["url"], timeout=120) as remote:
            raw = remote.read()
    else:
        raise RuntimeError(f"image API item had no b64_json/url: {json.dumps(item)[:200]}")
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(raw)
    return out


def generate(
    prompt: str,
    out_path: str | Path,
    *,
    config: ImageProviderConfig,
    size: str = DEFAULT_SIZE,
    extra: dict | None = None,
) -> Path:
    """Text -> image via POST /images/generations.

    ``extra`` passes optional provider params straight through (e.g. ``background``,
    ``quality``, ``output_format``, ``n``).
    """
    payload = {"model": config.model, "prompt": prompt, "size": size}
    if extra:
        payload.update(extra)
    response = _post(config, "/images/generations", json.dumps(payload).encode("utf-8"), "application/json")
    return _save_first_image(response, out_path)


def edit(
    prompt: str,
    image_paths: str | Path | Sequence[str | Path],
    out_path: str | Path,
    *,
    config: ImageProviderConfig,
    size: str = DEFAULT_SIZE,
    extra: dict | None = None,
) -> Path:
    """Reference image(s) + prompt -> image via multipart POST /images/edits.

    This is the character-anchoring path: pass a canonical character image (and
    optionally a previous frame) so the model keeps the same character.
    """
    paths = [Path(p) for p in ([image_paths] if isinstance(image_paths, (str, Path)) else list(image_paths))]
    if not paths:
        raise ValueError("edit requires at least one reference image")
    boundary = "----memeforge" + uuid.uuid4().hex
    chunks: list[bytes] = []

    def text_field(name: str, value: str) -> None:
        chunks.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode("utf-8")
        )

    text_field("model", config.model)
    text_field("prompt", prompt)
    text_field("size", size)
    for key, value in (extra or {}).items():
        text_field(key, str(value))
    for index, path in enumerate(paths):
        ctype = mimetypes.guess_type(path.name)[0] or "image/png"
        # `image[]` is the documented multipart field for GPT-image edits (accepts 1 or N).
        # A fixed ASCII filename sidesteps quoted-string escaping for odd source names.
        chunks.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="image[]"; '
            f'filename="ref{index}.png"\r\nContent-Type: {ctype}\r\n\r\n'.encode("utf-8")
        )
        chunks.append(path.read_bytes())
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    response = _post(config, "/images/edits", b"".join(chunks), f"multipart/form-data; boundary={boundary}")
    return _save_first_image(response, out_path)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Provider-agnostic OpenAI-compatible image client.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("generate", "edit"):
        sp = sub.add_parser(name)
        sp.add_argument("--prompt", required=True)
        sp.add_argument("--out", required=True)
        sp.add_argument("--size", default=DEFAULT_SIZE)
        sp.add_argument("--base-url")
        sp.add_argument("--api-key")
        sp.add_argument("--model")
        if name == "edit":
            sp.add_argument("--image", action="append", required=True, help="reference image path (repeatable)")
    args = parser.parse_args(argv)
    config = ImageProviderConfig.from_env(base_url=args.base_url, api_key=args.api_key, model=args.model)
    if args.command == "generate":
        out = generate(args.prompt, args.out, config=config, size=args.size)
    else:
        out = edit(args.prompt, args.image, args.out, config=config, size=args.size)
    print(f"SAVED {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
