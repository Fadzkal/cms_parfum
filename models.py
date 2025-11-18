from bson.objectid import ObjectId
from db_config import get_db
import time

# Inisialisasi database
db = get_db()

# --- Data Komponen Mesin (Hardcoded untuk Referensi) ---
MACHINE_COMPONENTS = {
    "mixing": [
        "Motor Agitator", "Agitator Blade / Impeller", "Gearbox / Reducer",
        "Temperature Sensor", "Level Sensor", "Heating Jacket",
        "Pressure Relief Valve", "Control Panel", "Gasket & Seal", "Output Valve"
    ],
    "filling": [
        "Nozzle Filling", "Filling Pump", "Flow Sensor", "Hopper",
        "Sensor Botol", "Solenoid Valve", "PLC Control", "Pneumatic Cylinder",
        "Tube & Hose", "Emergency Stop"
    ],
    "conveyor": [
        "Motor Conveyor", "Gearbox", "Conveyor Belt", "Roller",
        "Frame Body", "Sensor Photoelectric", "Inverter", "Bearing"
    ],
    "labeling": [
        "Label Dispenser", "Label Sensor", "Applicator Roller", "Bottle Sensor",
        "Stepper Motor", "PLC Unit", "Mini Conveyor", "Tension Control"
    ]
}

# ==========================================
# 1. USERS COLLECTION
# ==========================================
def get_user_collection():
    if db is not None:
        return db['users']
    return None

def create_initial_users():
    users = get_user_collection()
    # PERBAIKAN: Menggunakan 'is not None'
    if users is not None and users.count_documents({}) == 0:
        initial_users = [
            {"username": "op_lina", "password": "123", "role": "Operator", "name": "Lina Operator", "department": "Production"},
            {"username": "tech_budi", "password": "123", "role": "Teknisi", "name": "Budi Teknisi", "department": "Maintenance"},
            {"username": "sup_adi", "password": "123", "role": "Supervisor", "name": "Adi Supervisor", "department": "Maintenance"},
            {"username": "mgr_maya", "password": "123", "role": "Manager", "name": "Maya Manager", "department": "Management"}
        ]
        users.insert_many(initial_users)
        print("User awal berhasil dibuat.")

def register_new_user(username, password, role, name, department):
    """Mendaftarkan user baru ke database."""
    users = get_user_collection()
    
    # PERBAIKAN: Cek apakah koleksi ada
    if users is None:
        return False, "Database tidak terkoneksi"

    # Cek duplikasi username
    if users.find_one({"username": username}):
        return False, "Username sudah terdaftar."

    new_user_data = {
        "username": username,
        "password": password,
        "role": role,
        "name": name,
        "department": department
    }
    
    try:
        result = users.insert_one(new_user_data)
        return True, str(result.inserted_id)
    except Exception as e:
        return False, f"Gagal menyimpan data: {e}"


# ==========================================
# 2. ASSETS COLLECTION
# ==========================================
def get_asset_collection():
    if db is not None:
        return db['assets']
    return None

def create_initial_assets():
    assets = get_asset_collection()
    # PERBAIKAN: Menggunakan 'is not None'
    if assets is not None and assets.count_documents({}) == 0:
        initial_assets = [
            {
                "name": "Mixing Tank A", 
                "location": "Area Pencampuran", 
                "critical_components": MACHINE_COMPONENTS["mixing"],
                "status": "Operasi Normal",
                "type": "mixing",
                "breakdown_count": 2,
                "last_maintenance": int(time.time()) - 86400,
                "efficiency": 95.5
            },
            {
                "name": "Filling Machine 01", 
                "location": "Lini Pengisian", 
                "critical_components": MACHINE_COMPONENTS["filling"],
                "status": "Perlu Perhatian",
                "type": "filling",
                "breakdown_count": 5,
                "last_maintenance": int(time.time()) - 172800,
                "efficiency": 87.2
            },
            {
                "name": "Conveyor Line A", 
                "location": "Lini Pengisian", 
                "critical_components": MACHINE_COMPONENTS["conveyor"],
                "status": "Operasi Normal",
                "type": "conveyor",
                "breakdown_count": 1,
                "last_maintenance": int(time.time()) - 259200,
                "efficiency": 92.8
            },
            {
                "name": "Labeling Machine B", 
                "location": "Lini Pengemasan", 
                "critical_components": MACHINE_COMPONENTS["labeling"],
                "status": "Bermasalah",
                "type": "labeling",
                "breakdown_count": 8,
                "last_maintenance": int(time.time()) - 345600,
                "efficiency": 76.4
            },
        ]
        assets.insert_many(initial_assets)
        print("Aset awal berhasil dibuat.")


# ==========================================
# 3. WORK ORDERS (WO) COLLECTION
# ==========================================
def get_wo_collection():
    if db is not None:
        return db['work_orders']
    return None


# ==========================================
# 4. INVENTORY COLLECTION
# ==========================================
def get_inventory_collection():
    if db is not None:
        return db['inventory']
    return None

def create_initial_inventory():
    inventory = get_inventory_collection()
    # PERBAIKAN: Menggunakan 'is not None'
    if inventory is not None and inventory.count_documents({}) == 0:
        initial_inventory = []
        
        # Buat inventory untuk semua komponen
        for machine_type, components in MACHINE_COMPONENTS.items():
            for component in components:
                initial_inventory.append({
                    "item_name": component,
                    "part_number": f"PART-{machine_type.upper()}-{components.index(component)+1:02d}",
                    "machine_type": machine_type,
                    "current_stock": 15,
                    "min_stock": 5,
                    "unit": "pcs",
                    "status": "Aman",
                    "value": 2500000
                })
        
        inventory.insert_many(initial_inventory)
        print("Inventory awal berhasil dibuat.")


# ==========================================
# 5. MAINTENANCE SCHEDULE COLLECTION
# ==========================================
def get_schedule_collection():
    if db is not None:
        return db['maintenance_schedule']
    return None

def create_initial_schedule():
    schedule = get_schedule_collection()
    # PERBAIKAN: Menggunakan 'is not None'
    if schedule is not None and schedule.count_documents({}) == 0:
        initial_schedule = [
            {
                "asset_name": "Mixing Tank A",
                "type": "Preventif",
                "description": "Pembersihan dan inspeksi rutin",
                "scheduled_date": int(time.time()) + 86400,
                "status": "Dijadwalkan",
                "assigned_to": "tech_budi",
                "duration": 2
            }
        ]
        schedule.insert_many(initial_schedule)
        print("Jadwal maintenance awal berhasil dibuat.")


# --- Auto Init jika dijalankan langsung ---
if __name__ == '__main__':
    # PERBAIKAN: Cek db is not None sebelum inisialisasi
    if db is not None:
        create_initial_users()
        create_initial_assets()
        create_initial_inventory()
        create_initial_schedule()
    else:
        print("Gagal terhubung ke database, inisialisasi dibatalkan.")