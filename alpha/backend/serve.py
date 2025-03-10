from flask import Flask, send_from_directory
import os


def setup_file_serving(app):
    # Configuration
    PORT = 5000
    HOST = "0.0.0.0"  # This allows external access
    PUBLIC_FOLDER = "public"

    # Ensure public directory exists
    os.makedirs(PUBLIC_FOLDER, exist_ok=True)

    @app.route("/")
    def serve_index():
        return send_from_directory("public", "index.html")

    @app.route("/<path:path>")
    def serve_public(path):
        return send_from_directory("public", path)

    # Set the port and host in the app configuration
    app.config["PORT"] = PORT
    app.config["HOST"] = HOST

    # Add run configuration
    def run_server():
        app.run(host=HOST, port=PORT, debug=True)  # Set to False in production

    app.run_server = run_server

    return app
