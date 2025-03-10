import os
import datetime
import zipfile
import io
import shutil
import hashlib
import time
import uuid
from werkzeug.utils import secure_filename
from flask import send_file, jsonify, Response, request, current_app
import threading
import json

# Database paths
DATABASE_PATHS = [
    "database/books_data.db",
    "database/books_static.db"
]

# Store ongoing operations for status checks
OPERATIONS = {}


def setup_backup_routes(app):
    # Create required directories
    os.makedirs('temp_uploads', exist_ok=True)
    os.makedirs('temp_backups', exist_ok=True)

    @app.route('/backup', methods=['GET'])
    def backup_database():
        """
        Create a zip backup of all database files and send it to the client.
        Uses chunked transfer encoding for reliable download on slow connections.
        Supports range requests for resumable downloads.
        """
        try:
            # Check if all database files exist
            for db_path in DATABASE_PATHS:
                if not os.path.exists(db_path):
                    return jsonify({"error": f"Database file {db_path} not found"}), 404

            # Create a timestamped backup filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"books_db_backup_{timestamp}.zip"
            backup_path = os.path.join('temp_backups', backup_filename)

            # Create zip file on disk first (more reliable for large files)
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for db_path in DATABASE_PATHS:
                    zf.write(db_path, os.path.basename(db_path))

            # Calculate file size and checksum for verification
            file_size = os.path.getsize(backup_path)
            checksum = calculate_file_checksum(backup_path)

            # Get chunk size from request - default to 1MB if not specified
            chunk_size = request.args.get(
                'chunk_size', default=1024*1024, type=int)

            # Support for range requests (resumable downloads)
            range_header = request.headers.get('Range', None)
            start, end = 0, file_size - 1

            if range_header:
                try:
                    range_match = range_header.replace('bytes=', '').split('-')
                    start = int(range_match[0]) if range_match[0] else 0
                    end = int(
                        range_match[1]) if range_match[1] else file_size - 1
                except (ValueError, IndexError):
                    return jsonify({"error": "Invalid range header"}), 400

            # Ensure start is within bounds
            if start >= file_size:
                return jsonify({"error": "Range not satisfiable"}), 416

            # Adjust end if it's beyond the file size
            if end >= file_size:
                end = file_size - 1

            # Calculate the length of the content to be sent
            content_length = end - start + 1

            # Create a generator to stream the file in chunks
            def generate():
                with open(backup_path, 'rb') as f:
                    f.seek(start)
                    remaining = content_length
                    while remaining > 0:
                        read_size = min(chunk_size, remaining)
                        data = f.read(read_size)
                        if not data:
                            break
                        remaining -= len(data)
                        yield data

                # Schedule file cleanup after streaming
                threading.Thread(target=lambda: cleanup_file_later(
                    backup_path, 600)).start()

            # Prepare appropriate headers
            headers = {
                'Content-Disposition': f'attachment; filename={backup_filename}',
                'Accept-Ranges': 'bytes',
                'Cache-Control': 'no-cache',
                'Content-Length': str(content_length),
                'X-Checksum': checksum,
                'X-Total-Size': str(file_size)
            }

            # Respond with 206 if it's a partial content request
            status_code = 206 if range_header else 200
            if range_header:
                headers['Content-Range'] = f'bytes {start}-{end}/{file_size}'

            return Response(
                generate(),
                status=status_code,
                mimetype='application/zip',
                headers=headers
            )

        except Exception as e:
            return jsonify({"error": f"Backup failed: {str(e)}"}), 500

    @app.route('/backup/verify', methods=['GET'])
    def verify_backup():
        """
        Verify a backup file by comparing checksums.
        """
        checksum = request.args.get('checksum')
        filename = request.args.get('filename')

        if not checksum or not filename:
            return jsonify({"error": "Missing checksum or filename"}), 400

        backup_path = os.path.join('temp_backups', secure_filename(filename))

        if not os.path.exists(backup_path):
            return jsonify({"error": "Backup file not found"}), 404

        calculated_checksum = calculate_file_checksum(backup_path)

        if calculated_checksum == checksum:
            return jsonify({"verified": True}), 200
        else:
            return jsonify({
                "verified": False,
                "expected": calculated_checksum,
                "received": checksum
            }), 200

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

    @app.route('/restore', methods=['POST'])
    def restore_database():
        """
        Restore databases from a zip backup file.
        Supports chunked upload for reliability on slow connections.
        """
        # Check for chunk upload
        is_chunk = 'chunk' in request.form
        upload_id = request.form.get('upload_id', str(uuid.uuid4()))

        # For the initial request or single-part upload
        if not is_chunk or request.form.get('chunk') == '0':
            # Create a new operation for tracking
            OPERATIONS[upload_id] = {
                'type': 'restore',
                'status': 'uploading',
                'started_at': time.time(),
                'chunks_received': 0,
                'total_chunks': int(request.form.get('total_chunks', 1)),
                'temp_dir': os.path.join('temp_uploads', upload_id)
            }

            # Create temporary directory for chunks
            os.makedirs(OPERATIONS[upload_id]['temp_dir'], exist_ok=True)

        # For ongoing uploads, check if operation exists
        elif upload_id not in OPERATIONS:
            return jsonify({"error": "Upload session not found"}), 404

        try:
            # Get the file chunk
            if 'backup_file' not in request.files:
                return jsonify({"error": "No backup file provided"}), 400

            file = request.files['backup_file']
            if file.filename == '':
                return jsonify({"error": "No backup file selected"}), 400

            if is_chunk:
                # Save this chunk
                chunk_number = int(request.form.get('chunk'))
                chunk_path = os.path.join(
                    OPERATIONS[upload_id]['temp_dir'], f"chunk_{chunk_number}")
                file.save(chunk_path)

                # Update operation status
                OPERATIONS[upload_id]['chunks_received'] += 1

                # Check if we have all chunks
                if OPERATIONS[upload_id]['chunks_received'] >= OPERATIONS[upload_id]['total_chunks']:
                    # All chunks received, combine them
                    combined_file_path = os.path.join(
                        OPERATIONS[upload_id]['temp_dir'], "combined.zip")
                    with open(combined_file_path, 'wb') as combined_file:
                        for i in range(OPERATIONS[upload_id]['total_chunks']):
                            chunk_path = os.path.join(
                                OPERATIONS[upload_id]['temp_dir'], f"chunk_{i}")
                            with open(chunk_path, 'rb') as chunk_file:
                                combined_file.write(chunk_file.read())

                    # Verify checksum if provided
                    client_checksum = request.form.get('checksum')
                    if client_checksum:
                        calculated_checksum = calculate_file_checksum(
                            combined_file_path)
                        if calculated_checksum != client_checksum:
                            OPERATIONS[upload_id]['status'] = 'failed'
                            return jsonify({
                                "error": "Checksum verification failed",
                                "upload_id": upload_id,
                                "expected": client_checksum,
                                "calculated": calculated_checksum
                            }), 400

                    # Proceed with restore
                    return perform_restore(combined_file_path, upload_id)
                else:
                    # More chunks expected
                    return jsonify({
                        "success": True,
                        "upload_id": upload_id,
                        "message": f"Chunk {chunk_number} received successfully",
                        "chunks_received": OPERATIONS[upload_id]['chunks_received'],
                        "total_chunks": OPERATIONS[upload_id]['total_chunks']
                    }), 200
            else:
                # Single file upload
                temp_path = os.path.join(
                    OPERATIONS[upload_id]['temp_dir'], "backup.zip")
                file.save(temp_path)

                # Verify checksum if provided
                client_checksum = request.form.get('checksum')
                if client_checksum:
                    calculated_checksum = calculate_file_checksum(temp_path)
                    if calculated_checksum != client_checksum:
                        OPERATIONS[upload_id]['status'] = 'failed'
                        return jsonify({
                            "error": "Checksum verification failed",
                            "upload_id": upload_id,
                            "expected": client_checksum,
                            "calculated": calculated_checksum
                        }), 400

                # Proceed with restore
                return perform_restore(temp_path, upload_id)

        except zipfile.BadZipFile:
            OPERATIONS[upload_id]['status'] = 'failed'
            return jsonify({"error": "Invalid zip file provided", "upload_id": upload_id}), 400
        except Exception as e:
            OPERATIONS[upload_id]['status'] = 'failed'
            return jsonify({"error": f"Restore failed: {str(e)}", "upload_id": upload_id}), 500

    @app.route('/operation/status/<upload_id>', methods=['GET'])
    def operation_status(upload_id):
        """
        Check the status of an ongoing operation.
        """
        if upload_id not in OPERATIONS:
            return jsonify({"error": "Operation not found"}), 404

        return jsonify(OPERATIONS[upload_id]), 200

    def perform_restore(zip_path, operation_id):
        """
        Process a zip file for database restoration.
        """
        try:
            # Update operation status
            OPERATIONS[operation_id]['status'] = 'restoring'

            # Verify the zip file
            if not zipfile.is_zipfile(zip_path):
                OPERATIONS[operation_id]['status'] = 'failed'
                return jsonify({"error": "Invalid zip file", "upload_id": operation_id}), 400

            # Dictionary to track restored files
            restored_files = []

            # Create a backup of current databases before restoring
            backup_current_databases()

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Get list of files in the zip
                file_list = zip_ref.namelist()

                # Create database directory if it doesn't exist
                os.makedirs(os.path.dirname(DATABASE_PATHS[0]), exist_ok=True)

                # Extract only the database files we care about
                for db_path in DATABASE_PATHS:
                    base_name = os.path.basename(db_path)
                    if base_name in file_list:
                        # Extract the file to its destination path
                        with zip_ref.open(base_name) as source, open(db_path, 'wb') as target:
                            shutil.copyfileobj(source, target)
                        restored_files.append(db_path)

            if not restored_files:
                OPERATIONS[operation_id]['status'] = 'failed'
                return jsonify({
                    "error": "No valid database files found in the backup",
                    "upload_id": operation_id
                }), 400

            # Update operation status
            OPERATIONS[operation_id]['status'] = 'completed'
            OPERATIONS[operation_id]['completed_at'] = time.time()
            OPERATIONS[operation_id]['restored_files'] = restored_files

            # Schedule cleanup
            threading.Thread(target=lambda: cleanup_operation_later(
                operation_id, 3600)).start()

            return jsonify({
                "success": True,
                "message": "Database restore completed successfully",
                "restored_files": restored_files,
                "upload_id": operation_id
            }), 200

        except Exception as e:
            OPERATIONS[operation_id]['status'] = 'failed'
            OPERATIONS[operation_id]['error'] = str(e)
            return jsonify({"error": f"Restore failed: {str(e)}", "upload_id": operation_id}), 500


def backup_current_databases():
    """
    Create a backup of the current database files before restoration.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for db_path in DATABASE_PATHS:
        if os.path.exists(db_path):
            # Create a timestamped backup file
            backup_path = f"{db_path}.{timestamp}.bak"
            shutil.copy2(db_path, backup_path)

    return True


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


def calculate_file_checksum(file_path):
    """
    Calculate the MD5 checksum of a file.
    """
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        # Read the file in chunks to handle large files
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def cleanup_file_later(file_path, delay_seconds):
    """
    Delete a file after a specified delay.
    """
    time.sleep(delay_seconds)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass


def cleanup_operation_later(operation_id, delay_seconds):
    """
    Clean up operation data after a specified delay.
    """
    time.sleep(delay_seconds)
    try:
        if operation_id in OPERATIONS:
            # Clean up temp files
            temp_dir = OPERATIONS[operation_id].get('temp_dir')
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

            # Remove operation from tracking
            del OPERATIONS[operation_id]
    except Exception:
        pass
