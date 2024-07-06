from main import app
import logging

if __name__ == "__main__":
    from waitress import serve
    logging.basicConfig(level=logging.DEBUG)
    serve(app, host="0.0.0.0", port=5000)
