"""
The web page for the agent: vetra/web.html, a plain chat page whose one difference from a
general chatbot is that every answer shows the official documents it cites, as numbered
markers in the text and source cards beneath it. RTI questions still reach rag/ through the agent.

Run:  python -m vetra.web                  http://127.0.0.1:8000
      python -m vetra.web --port 8080 --no-browser
      python -m vetra.web --host 0.0.0.0   every interface (for Docker)
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import os
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import agent, jurisdictions, languages, llm, text_index
from .domains import DOMAINS
from .knowledge import UNOFFICIAL, Knowledge

PAGE = Path(__file__).resolve().parent / "web.html"
TITLE = "VETRA: your government, from its own documents"
BLURB = ("Ask about farm schemes, crop insurance, pensions, taxes and budgets anywhere in India, or about the "
         "Right to Information Act. A simple question gets a short answer, and a bigger one gets a full brief. "
         "Every answer comes from official documents. Not legal advice.")
PLACEHOLDER = "Ask about a farm scheme, crop insurance, a pension, or RTI…"
EXAMPLES = ("what is the last date to insure my cashew crop under weather insurance",
            "i grow paddy in rabi, how much premium do i pay under PMFBY",
            "explain crop insurance in andhra pradesh in detail",
            "what is pm kisan and who gets it",
            "how do i get a kisan credit card",
            "how does atal pension yojana work",
            "how much is the rti fee")
class Server(ThreadingHTTPServer):
    """On Windows, address reuse lets a second server bind a port that is already in use, and requests
    then go to either one: an old server with old settings answered a citizen. So a busy port fails there."""
    allow_reuse_address = os.name != "nt"


PIPELINE = threading.Lock()  # one question at a time: shared rate limits and search models

_CITATION = re.compile(r"\[E(\d+)\]")


def page_html() -> str:
    page = PAGE.read_text(encoding="utf-8")
    states = '<option value="">All India</option>' + "".join(
        f'<option value="{code}">{html.escape(name)}</option>'
        for code, name in sorted(jurisdictions.STATES.items(), key=lambda pair: pair[1]))
    replies = '<option value="auto">Same language as the question</option>' + "".join(
        f'<option value="{code}">{html.escape(name)}</option>' for code, name in languages.NAMES.items())
    starters = "".join(f'<button class="starter" type="button">{html.escape(q)}</button>' for q in EXAMPLES[:4])
    return (page.replace("{{STATE_OPTIONS}}", states).replace("{{REPLY_OPTIONS}}", replies)
            .replace("{{STARTERS}}", starters))


def _host(url: str | None) -> str:
    match = re.match(r"https?://(?:www\.)?([^/:]+)", url or "")
    return match.group(1) if match else ""


def to_page(r: agent.Result) -> dict:
    """The agent's result, in the shape the page already renders."""
    steps = r.trace.get("steps") or []
    label = DOMAINS[r.domain].label if r.domain in DOMAINS else None
    return {"domain": r.domain, "domain_label": label, "routed": bool(label), "language": r.language,
            "reply_language": r.language, "answer": _CITATION.sub(r"[\1]", r.answer),
            "standalone": "", "passage": None, "model": steps[-1]["model"] if steps else "no model",
            "search_s": r.trace.get("seconds", 0), "answer_s": 0, "coverage": r.coverage,
            "sources": [{"n": s["n"], "doc": s["doc"], "source": s["doc"] + (f" · {s['kind']}" if s.get("kind") else ""),
                         "url": s.get("url"), "host": _host(s.get("url")), "date": s.get("date"),
                         "status": s.get("status"), "kind": s.get("kind") or "", "scanned": bool(s.get("scanned")),
                         "unofficial": s.get("kind") in UNOFFICIAL, "reviewed": bool(s.get("reviewed")),
                         "added": bool(s.get("added_because")), "text": s.get("text", "")}
                        for s in r.sources]}


class Handler(BaseHTTPRequestHandler):
    models: llm.Models
    knowledge: Knowledge

    def do_GET(self) -> None:
        if self.path not in ("/", "/index.html"):
            self.send_error(404)
            return
        self._send(200, page_html().encode("utf-8"), "text/html; charset=utf-8")

    def do_POST(self) -> None:
        if self.path != "/ask":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > 200_000:
                self._json(413, {"error": "That request is too long."})
                return
            payload = json.loads(self.rfile.read(length) or b"{}")
            question = str(payload.get("question", "")).strip()
            history = [{"q": str(t["q"])[:1000], "a": str(t["a"])[:2000]}
                       for t in (payload.get("history") or [])[-3:]
                       if isinstance(t, dict) and t.get("q") and t.get("a")]
            state = jurisdictions.normalise(str(payload.get("state") or ""))
            reply = payload.get("reply")
        except (ValueError, TypeError, AttributeError):
            self._json(400, {"error": "Type a question first."})
            return
        if not question:
            self._json(400, {"error": "Type a question first."})
            return
        if len(question) > agent.MAX_QUESTION:
            self._json(400, {"error": f"Keep the question under {agent.MAX_QUESTION} characters."})
            return
        with PIPELINE:
            try:
                result = agent.answer(question, history, state, self.models, self.knowledge, reply=reply)
            except Exception as exc:  # the page must always get an answer it can show
                print(f"  error: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
                self._json(503, {"error": "The assistant hit a problem. Please try again in a minute."})
                return
        print(f"Q [{result.kind} {result.domain} {result.state or '-'}] {result.trace.get('needs')} "
              f"calls={result.trace.get('calls')} {result.trace.get('seconds')}s", flush=True)
        self._json(200, to_page(result))

    def _json(self, code: int, obj: dict) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    started = time.perf_counter()
    Handler.models = llm.from_env()
    Handler.knowledge = Knowledge()
    # Load search now, so the first citizen doesn't wait for it.
    for name, domain in DOMAINS.items():
        if not domain.legacy and text_index.corpus(name):
            text_index.search("loading", name, None)
    try:
        server = Server((args.host, args.port), Handler)
    except OSError:
        print(f"Port {args.port} is already in use. Try:  python -m vetra.web --port 8080")
        return 1
    url = f"http://{'127.0.0.1' if args.host in ('0.0.0.0', '::') else args.host}:{args.port}"
    print(f"ready in {time.perf_counter() - started:.0f}s\nopen {url}   (Ctrl+C to stop)", flush=True)
    if not args.no_browser:
        threading.Timer(0.5, webbrowser.open, [url]).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
