from flask import Flask, request, jsonify, render_template
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import uuid

load_dotenv()

app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    # Buat nama unik supaya tidak bentrok
    ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_bytes = file.read()

    # Upload ke Supabase Storage
    supabase.storage.from_(SUPABASE_BUCKET).upload(
        path=unique_filename,
        file=file_bytes,
        file_options={"content-type": file.content_type}
    )

    # Ambil public URL
    public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(unique_filename)

    return jsonify({
        "message": "Upload berhasil!",
        "filename": file.filename,
        "url": public_url
    })

@app.route("/files", methods=["GET"])
def list_files():
    response = supabase.storage.from_(SUPABASE_BUCKET).list()
    files = []
    for f in response:
        name = f["name"]
        url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(name)
        files.append({"name": name, "url": url})
    return jsonify(files)

@app.route("/delete/<filename>", methods=["DELETE"])
def delete_file(filename):
    supabase.storage.from_(SUPABASE_BUCKET).remove([filename])
    return jsonify({"message": f"{filename} berhasil dihapus"})

if __name__ == "__main__":
    app.run(debug=True)