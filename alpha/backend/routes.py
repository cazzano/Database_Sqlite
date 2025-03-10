from flask import request, jsonify
from crud_books_data import (
    add_book,
    get_all_books,
    get_book_by_id,
    update_book,
    delete_book
)
from crud_books_static import (
    add_book_static,
    get_book_static,
    update_book_static,
    delete_book_static,
    get_all_books_static
)


def setup_routes(app):
    @app.route('/')
    def home():
        return "Welcome to the Books Database App!"

    # Book CRUD routes
    @app.route('/books/add', methods=['POST'])
    def add_book_route():
        data = request.json
        if not all(key in data for key in ['name', 'author_name', 'books_id']):
            return jsonify({"message": "Missing required fields"}), 400

        if add_book(
            data['name'],
            data['author_name'],
            data['books_id'],
            data.get('category'),
            data.get('description')
        ):
            # If static resources are provided, add them too
            if 'picture_url' in data or 'download_url' in data:
                add_book_static(
                    data['books_id'],
                    data.get('picture_url'),
                    data.get('download_url')
                )
            return jsonify({"message": "Book added successfully"}), 201
        return jsonify({"message": "Failed to add book"}), 400

    @app.route('/books', methods=['GET'])
    def get_all_books_route():
        books = get_all_books()
        books_list = []
        for book in books:
            static_data = get_book_static(book[0])  # book[0] is books_id
            book_dict = {
                "books_id": book[0],
                "name": book[1],
                "author_name": book[2],
                "category": book[3],
                "description": book[4],
                "static_resources": {
                    "picture_url": static_data[1] if static_data else None,
                    "download_url": static_data[2] if static_data else None
                } if static_data else None
            }
            books_list.append(book_dict)
        return jsonify(books_list), 200

    @app.route('/books/<int:books_id>', methods=['GET'])
    def get_book_by_id_route(books_id):
        book = get_book_by_id(books_id)
        if not book:
            return jsonify({"message": "Book not found"}), 404

        static_data = get_book_static(books_id)
        book_dict = {
            "books_id": book[0],
            "name": book[1],
            "author_name": book[2],
            "category": book[3],
            "description": book[4],
            "static_resources": {
                "picture_url": static_data[1] if static_data else None,
                "download_url": static_data[2] if static_data else None
            } if static_data else None
        }
        return jsonify(book_dict), 200

    @app.route('/books/update/<int:books_id>', methods=['PUT'])
    def update_book_route(books_id):
        data = request.json
        book_updated = update_book(
            books_id,
            data.get('name'),
            data.get('author_name'),
            data.get('category'),
            data.get('description')
        )

        # Handle static resource updates if provided
        static_updated = True
        if 'picture_url' in data or 'download_url' in data:
            static_updated = update_book_static(
                books_id,
                data.get('picture_url'),
                data.get('download_url')
            )

        if book_updated and static_updated:
            return jsonify({"message": "Book updated successfully"}), 200
        return jsonify({"message": "Failed to update book"}), 400

    @app.route('/books/delete/<int:books_id>', methods=['DELETE'])
    def delete_book_route(books_id):
        # Delete static resources first (if they exist)
        delete_book_static(books_id)

        if delete_book(books_id):
            return jsonify({"message": "Book and associated resources deleted successfully"}), 200
        return jsonify({"message": "Failed to delete book"}), 400

    # Static resources specific routes
    @app.route('/books/static', methods=['GET'])
    def get_all_books_static_route():
        static_data = get_all_books_static()
        if not static_data:
            return jsonify([]), 200

        result = []
        for data in static_data:
            result.append({
                "books_id": data[0],
                "picture_url": data[1],
                "download_url": data[2]
            })
        return jsonify(result), 200

    @app.route('/books/static/add/<int:books_id>', methods=['POST'])
    def add_book_static_route(books_id):
        data = request.json
        if add_book_static(books_id, data.get('picture_url'), data.get('download_url')):
            return jsonify({"message": "Static resources added successfully"}), 201
        return jsonify({"message": "Failed to add static resources"}), 400

    @app.route('/books/static/<int:books_id>', methods=['GET'])
    def get_book_static_route(books_id):
        static_data = get_book_static(books_id)
        if static_data:
            return jsonify({
                "books_id": static_data[0],
                "picture_url": static_data[1],
                "download_url": static_data[2]
            }), 200
        return jsonify({"message": "Static resources not found"}), 404

    @app.route('/books/static/update/<int:books_id>', methods=['PUT'])
    def update_book_static_route(books_id):
        data = request.json
        if update_book_static(books_id, data.get('picture_url'), data.get('download_url')):
            return jsonify({"message": "Static resources updated successfully"}), 200
        return jsonify({"message": "Failed to update static resources"}), 400

    @app.route('/books/static/delete/<int:books_id>', methods=['DELETE'])
    def delete_book_static_route(books_id):
        if delete_book_static(books_id):
            return jsonify({"message": "Static resources deleted successfully"}), 200
        return jsonify({"message": "Failed to delete static resources"}), 400
