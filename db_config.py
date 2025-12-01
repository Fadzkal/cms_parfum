# db_config.py
from pymongo import MongoClient

# Konfigurasi MongoDB
MONGO_URI = "mongodb://localhost:27017/" 
DB_NAME = "mms_parfum_db"

def get_db():
    """Membuat dan mengembalikan objek database."""
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        # Baris print di bawah ini saya comment agar terminal tidak penuh spam
        # print(f"Berhasil terhubung ke MongoDB: {DB_NAME}")
        return db
    except Exception as e:
        print(f"Gagal terhubung ke MongoDB: {e}")
        return None

# Contoh penggunaan (Hanya jalan jika file ini di-run langsung):
if __name__ == '__main__':
    db = get_db()
    
    # --- PERBAIKAN PENTING DI SINI ---
    # Pymongo baru melarang penggunaan "if db:". 
    # Harus diganti menjadi "if db is not None:"
    if db is not None:
        print(f"Tes Koneksi Sukses ke: {DB_NAME}")
        print("Koleksi yang tersedia:", db.list_collection_names())
    else:
        print("Gagal koneksi database.")