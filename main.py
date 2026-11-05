import argparse

import uvicorn


def _find_free_port(host: str, start_port: int, max_tries: int = 20) -> int:
    import socket

    port = int(start_port)
    for _ in range(max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((host, port))
                return port
            except OSError:
                port += 1
    raise RuntimeError(f"No free port found starting at {start_port} (tried {max_tries} ports).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Smart Driver Monitoring System (Web UI)")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    args = parser.parse_args()

    host = str(args.host)
    preferred_port = int(args.port)
    port = _find_free_port(host, preferred_port)
    if port != preferred_port:
        print(f"Port {preferred_port} is busy. Using {port} instead.")
    print(f"Open in your browser: http://{host}:{port}")

    uvicorn.run("web_app:app", host=host, port=port, reload=False, log_level="info")


if __name__ == "__main__":
    main()
