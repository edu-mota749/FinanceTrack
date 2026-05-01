import os

from waitress import serve

from app import app


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    print(f"Starting Waitress on 0.0.0.0:{port}")
    serve(app, host="0.0.0.0", port=port)