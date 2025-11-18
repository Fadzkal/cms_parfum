# db_config.py

from pymongo import MongoClient

# Konfigurasi MongoDB
MONGO_URI = "mongodb://localhost:27017/"  # Ganti jika server MongoDB Anda berbeda
DB_NAME = "mms_parfum_db"

def get_db():
    """Membuat dan mengembalikan objek database."""
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        print(f"Berhasil terhubung ke MongoDB: {DB_NAME}")
        return db
    except Exception as e:
        print(f"Gagal terhubung ke MongoDB: {e}")
        # Dalam aplikasi nyata, ini harus memicu logging atau keluar
        return None

# Contoh penggunaan (opsional):
if __name__ == '__main__':
    db = get_db()
    if db:
        # Cek koneksi dengan mencetak nama koleksi
        print("Koleksi yang tersedia:", db.list_collection_names())