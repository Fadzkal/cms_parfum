# init_database.py
from models import create_initial_users, create_initial_assets, create_initial_inventory, create_initial_schedule, create_initial_work_orders, db

if __name__ == '__main__':
    if db is not None:
        print("Memulai inisialisasi database dengan data realistis...")
        create_initial_users()
        create_initial_assets() 
        create_initial_inventory()
        create_initial_schedule()
        create_initial_work_orders() 
        print("Database initialized successfully with clean, realistic data!")
        print("Tidak ada data dummy WO atau schedule - sistem siap untuk data real.")
    else:
        print("Inisialisasi Gagal: Koneksi database bermasalah.")