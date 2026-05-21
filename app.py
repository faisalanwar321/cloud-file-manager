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

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt', 'xlsx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

    # Validasi tipe file
    if not allowed_file(file.filename):
        return jsonify({"error": "Tipe file tidak diizinkan!"}), 400

    # Validasi ukuran file
    file_bytes = file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        return jsonify({"error": "Ukuran file melebihi batas 10MB!"}), 400

    ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{ext}"

    supabase.storage.from_(SUPABASE_BUCKET).upload(
        path=unique_filename,
        file=file_bytes,
        file_options={"content-type": file.content_type}
    )

    public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(unique_filename)

    supabase.table("file_metadata").insert({
        "original_name": file.filename,
        "stored_name": unique_filename,
        "url": public_url
    }).execute()
    
    return jsonify({
        "message": "Upload berhasil!",
        "filename": file.filename,
        "url": public_url
    })

@app.route("/upload-private", methods=["POST"])
def upload_private_file():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Tipe file tidak diizinkan!"}), 400

    file_bytes = file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        return jsonify({"error": "Ukuran file melebihi batas 10MB!"}), 400

    ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{ext}"

    # Upload ke bucket PRIVAT
    supabase.storage.from_("private-uploads").upload(
        path=unique_filename,
        file=file_bytes,
        file_options={"content-type": file.content_type}
    )

    # Buat signed URL yang berlaku 1 jam
    signed = supabase.storage.from_("private-uploads").create_signed_url(
        unique_filename, 3600
    )
    signed_url = signed.get("signedURL") or signed.get("signed_url") or ""

    # Simpan metadata dengan tanda is_private = True
    supabase.table("file_metadata").insert({
        "original_name": file.filename,
        "stored_name": unique_filename,
        "url": signed_url,
        "is_private": True
    }).execute()

    return jsonify({
        "message": "Upload privat berhasil!",
        "filename": file.filename,
        "url": signed_url
    })

@app.route("/files", methods=["GET"])
def list_files():
    response = supabase.table("file_metadata").select("*").order("uploaded_at", desc=True).execute()
    files = []
    for f in response.data:
        files.append({
            "id": f["id"],
            "name": f["original_name"],
            "stored_name": f["stored_name"],
            "url": f["url"],
            "uploaded_at": f["uploaded_at"]
        })
    return jsonify(files)

@app.route("/delete/<filename>/<int:file_id>/<is_private>", methods=["DELETE"])
def delete_file(filename, file_id, is_private):
    bucket = "private-uploads" if is_private == "true" else SUPABASE_BUCKET
    supabase.storage.from_(bucket).remove([filename])
    supabase.table("file_metadata").delete().eq("id", file_id).execute()
    return jsonify({"message": f"{filename} berhasil dihapus"})

if __name__ == "__main__":
    app.run(debug=True)