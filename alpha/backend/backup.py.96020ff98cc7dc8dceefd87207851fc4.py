import os
import datetime
import zipfile
import io
from flask import send_file, jsonify, Response, request

# Database paths
DATABASE_PATHS = [
    "database/books_data.db",
    "database/books_static.db"
]


def setup_backup_routes(app):
    @app.route('/backup', methods=['GET'])
    def backup_database():
        """
        Create a zip backup of all database files and send it to the client.
        Uses chunked transfer encoding for reliable download on slow connections.
        """
        try:
            # Check if all database files exist
            for db_path in DATABASE_PATHS:
                if not os.path.exists(db_path):
                    return jsonify({"error": f"Database file {db_path} not found"}), 404

            # Create a timestamped backup filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"books_db_backup_{timestamp}.zip"

            # Create zip file in memory
            memory_file = io.BytesIO()
            with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                for db_path in DATABASE_PATHS:
                    zf.write(db_path, os.path.basename(db_path))

            # Reset pointer to start of the file
            memory_file.seek(0)

            # Get chunk size from request - default to 1MB if not specified
            chunk_size = request.args.get(
                'chunk_size', default=1024*1024, type=int)

            # Create a generator to stream the file in chunks
            def generate():
                data = memory_file.read(chunk_size)
                while data:
                    yield data
                    data = memory_file.read(chunk_size)

            # Use chunked transfer encoding with appropriate headers for reliable download
            response = Response(generate(), mimetype='application/zip')
            response.headers.set('Content-Disposition',
                                 f'attachment; filename={backup_filename}')
            response.headers.set('Transfer-Encoding', 'chunked')
            response.headers.set('Cache-Control', 'no-cache')
            return response

        except Exception as e:
            return jsonify({"error": f"Backup failed: {str(e)}"}), 500

    @app.route('/backup/status', methods=['GET'])
    def backup_status():
        """
        Check if all database files exist and return their sizes.
        """
        status = {
            "databases": [],
            "total_size_bytes": 0,
            "all_files_exist": True
        }

        for db_path in DATABASE_PATHS:
            db_info = {
                "path": db_path,
                "exists": os.path.exists(db_path)
            }

            if db_info["exists"]:
                size = os.path.getsize(db_path)
                db_info["size_bytes"] = size
                db_info["size_formatted"] = format_size(size)
                status["total_size_bytes"] += size
            else:
                db_info["size_bytes"] = 0
                db_info["size_formatted"] = "0 B"
                status["all_files_exist"] = False

            status["databases"].append(db_info)

        status["total_size_formatted"] = format_size(
            status["total_size_bytes"])
        return jsonify(status), 200


def format_size(size_bytes):
    """
    Format file size from bytes to human-readable format.
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1

    return f"{size_bytes:.2f} {size_names[i]}"
