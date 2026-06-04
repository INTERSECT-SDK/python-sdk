"""Minimal uvicorn entrypoint, main logic is in app/main.py."""

import argparse

import uvicorn


def main() -> None:
    """Very minimal uvicorn entrypoint. Allows customization of host and port."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()

    uvicorn.run(
        'examples.5_fastapi_example.app.main:app',
        host=args.host,
        port=args.port,
        server_header=False,
    )


if __name__ == '__main__':
    main()
