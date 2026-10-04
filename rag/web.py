"""
A minimal web page for asking questions, served locally.

No new dependencies: Python's built-in http.server serves one HTML page
(rag/web.html) and one JSON endpoint (POST /ask) that calls the same pipeline
as the terminal chat. Everything stays on this machine except the two Groq
calls the pipeline already makes.

Run:  python rag/web.py                 opens http://127.0.0.1:8000
      python rag/web.py --domain agriculture   the agriculture assistant
      python rag/web.py --port 8080     if 8000 is busy
      python rag/web.py --no-browser    don't open a browser tab

Connections are handled in parallel (Chrome opens idle "preconnect" sockets
that would freeze a single-threaded server), but questions run one at a time
behind a lock, so two quick clicks queue up instead of hitting Groq's
free-tier limit together.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import domains
from answer import MissingKey, answer_question
from retrieve import TOP_K, _collection, _corpus, _model

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PAGE = Path(__file__).with_name("web.html")
MAX_QUESTION = 500
PIPELINE = threading.Lock()  # one question through the pipeline at a time


class Handler(BaseHTTPRequestHandler):
    domain = "rti"  # set from --domain in main()

    def do_GET(self) -> None:
        if self.path not in ("/", "/index.html"):
            self.send_error(404)
            return
        # Read on every request, so edits to web.html show up on refresh.
        d = domains.get(self.domain)
        page = PAGE.read_text(encoding="utf-8")
        for key, value in {"PAGE_TITLE": d.title, "TITLE": d.title,
                           "BLURB": f"{d.blurb} Not legal advice.", "PLACEHOLDER": d.placeholder}.items():
            page = page.replace("{{" + key + "}}", html.escape(value))
        chips = "\n".join(f'        <button class="chip" type="button">{html.escape(q)}</button>'
                          for q in d.examples)
        page = page.replace("{{CHIPS}}", chips)
        self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")

    def do_POST(self) -> None:
        if self.path != "/ask":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            question = str(payload.get("question", "")).strip()
            # The page keeps the conversation and sends it back each time, so
            # the server holds no state. Accept only well-formed, bounded turns.
            history = [
                {"q": str(t["q"])[:1000], "a": str(t["a"])[:6000]}
                for t in (payload.get("history") or [])[-6:]
                if isinstance(t, dict) and t.get("q") and t.get("a")
            ]
        except (ValueError, json.JSONDecodeError, TypeError, AttributeError):
            question, history = "", []

        if not question:
            self._json(400, {"error": "Type a question first."})
            return
        if len(question) > MAX_QUESTION:
            self._json(400, {"error": f"Keep the question under {MAX_QUESTION} characters."})
            return

        print(f"\nQ: {question}" + (f"   ({len(history)} earlier turns)" if history else ""), flush=True)
        try:
            with PIPELINE:
                result = answer_question(question, TOP_K, history=history, domain=self.domain)
        except MissingKey as exc:
            print(f"   {exc}", flush=True)
            self._json(500, {"error": str(exc)})
            return
        except Exception as exc:  # network blip, retired model, rate limit on both models
            print(f"   failed: {exc}", flush=True)
            self._json(502, {"error": f"The answer service didn't respond ({type(exc).__name__}). "
                                      "Wait about 30 seconds and ask again."})
            return

        if result["standalone"] != question:
            print(f"   understood as: {result['standalone']}", flush=True)
        print(f"   search {result['search_s']:.1f}s, answer {result['answer_s']:.1f}s, "
              f"{result['model']}", flush=True)
        self._json(200, {
            "answer": result["answer"],
            "standalone": result["standalone"],
            "passage": result["passage"],
            "model": result["model"],
            "search_s": round(result["search_s"], 1),
            "answer_s": round(result["answer_s"], 1),
            "sources": [
                {
                    "n": n,
                    "source": hit["source"],
                    "added": bool(hit.get("added_because")),
                    "text": hit["text"],
                }
                for n, hit in enumerate(result["hits"], 1)
            ],
        })

    def _json(self, code: int, obj: dict) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass  # the browser closed the tab or gave up; nothing to do

    def log_message(self, fmt: str, *args) -> None:
        pass  # the default per-request log line is noise; questions are printed above


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--domain", default="rti", choices=list(domains.DOMAINS))
    args = parser.parse_args()
    Handler.domain = args.domain

    print(f"loading {args.domain} (about 30 seconds) ...", flush=True)
    started = time.perf_counter()
    _model(args.domain)
    _corpus(args.domain)
    count = _collection(args.domain).count()

    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError:
        print(f"Port {args.port} is already in use. Try:  python rag/web.py --port 8080")
        return 1

    url = f"http://127.0.0.1:{args.port}"
    print(f"ready in {time.perf_counter() - started:.0f}s ({count} chunks indexed)")
    print(f"open {url}   (Ctrl+C to stop)", flush=True)
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
