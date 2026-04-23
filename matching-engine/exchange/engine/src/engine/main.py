"""Entry point for the exchange engine.

Starts both the FastAPI admin server (with admin WS) and the client WebSocket server.
"""

from __future__ import annotations

import uvicorn

from engine.api import create_app
from engine.matching import MatchingEngine
from engine.ws_server import ExchangeWSServer


def main(
    api_host: str = "0.0.0.0",
    api_port: int = 8000,
    ws_host: str = "0.0.0.0",
    ws_port: int = 8765,
) -> None:
    engine = MatchingEngine()
    ws_server = ExchangeWSServer(engine=engine, host=ws_host, port=ws_port)
    app = create_app(engine=engine, ws_server=ws_server)

    print(f"Starting exchange engine...")
    print(f"  Admin API:        http://{api_host}:{api_port}")
    print(f"  Client WebSocket: ws://{ws_host}:{ws_port}")
    print(f"  Admin WebSocket:  ws://{api_host}:{api_port}/ws/admin")

    uvicorn.run(app, host=api_host, port=api_port)


if __name__ == "__main__":
    main()
