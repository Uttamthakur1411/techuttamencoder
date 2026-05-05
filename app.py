import os
import uuid
import io
from flask import Flask, render_template, request, send_file
from flask_sqlalchemy import SQLAlchemy
from cryptography.fernet import Fernet

app = Flask(__name__)

# CONFIG
app.config['UPLOAD_FOLDER'] = 'encrypted_storage'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

# folder create
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# DATABASE
class EncryptedFile(db.Model):
    id = db.Column(db.String(10), primary_key=True)
    original_name = db.Column(db.String(200))
    file_path = db.Column(db.String(300))

with app.app_context():
    db.create_all()

# 🔐 KEY (IMPORTANT: kabhi delete mat karna)
KEY_FILE = "secret.key"

def load_key():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)
    return open(KEY_FILE, "rb").read()

fernet = Fernet(load_key())

# HOME
@app.route('/')
def index():
    return render_template('index.html')

# 🔼 ENCODE
@app.route('/encode', methods=['POST'])
def encode():
    file = request.files.get('file')
    if not file:
        return "No file selected"

    try:
        unique_id = uuid.uuid4().hex[:8]

        file_data = file.read()
        encrypted_data = fernet.encrypt(file_data)

        path = os.path.join(app.config['UPLOAD_FOLDER'], unique_id + ".enc")
        with open(path, 'wb') as f:
            f.write(encrypted_data)

        db.session.add(EncryptedFile(
            id=unique_id,
            original_name=file.filename,
            file_path=path
        ))
        db.session.commit()

        return f"""
        <h2>✅ File Secured</h2>
        <h1>{unique_id}</h1>
        <a href="/">Back</a>
        """

    except Exception as e:
        return f"Error: {str(e)}"


# 🔽 DECODE (POST form se)
@app.route('/decode', methods=['POST'])
def decode_post():
    code = request.form.get('code')
    return process_decode(code)


# 🔽 DECODE (GET url se download)
@app.route('/decode/<code>')
def decode_get(code):
    return process_decode(code)


# 👁️ VIEW FILE
@app.route('/view/<code>')
def view_file(code):
    file_entry = EncryptedFile.query.filter_by(id=code).first()

    if not file_entry:
        return "❌ Invalid Code"

    try:
        with open(file_entry.file_path, 'rb') as f:
            encrypted_data = f.read()

        decrypted_data = fernet.decrypt(encrypted_data)

        return send_file(
            io.BytesIO(decrypted_data),
            download_name=file_entry.original_name
        )
    except Exception as e:
        return f"❌ View Failed: {str(e)}"


# 🔁 COMMON FUNCTION (reuse)
def process_decode(code):
    file_entry = EncryptedFile.query.filter_by(id=code).first()

    if not file_entry:
        return "❌ Invalid Code"

    try:
        with open(file_entry.file_path, 'rb') as f:
            encrypted_data = f.read()

        decrypted_data = fernet.decrypt(encrypted_data)

        return send_file(
            io.BytesIO(decrypted_data),
            download_name=file_entry.original_name,
            as_attachment=True
        )
    except Exception as e:
        return f"❌ Decryption Failed: {str(e)}"
if __name__ == '__main__':
    # Render environment variable se port uthayega
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)