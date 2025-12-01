# models.py
from bson.objectid import ObjectId
from db_config import get_db
import time
from datetime import datetime, timedelta

# Inisialisasi database
db = get_db()

# --- Data Komponen Mesin (Hardcoded untuk Referensi) ---
MACHINE_COMPONENTS = {
    "mixing": [
        "Motor Agitator", "Agitator Blade / Impeller", "Gearbox / Reducer", "Gasket & Seal"
    ],
    "filling": [
        "Nozzle Filling", "Filling Pump", "Flow Sensor", "Solenoid Valve"
    ],
    "conveyor": [
        "Motor Conveyor", "Conveyor Belt", "Roller", "Bearing"
    ],
    "labeling": [
        "Label Dispenser", "Label Sensor", "Applicator Roller", "Stepper Motor"
    ]
}

# Fungsi Helper untuk Waktu (Timestamp dalam detik)
def days_ago(days):
    return int((datetime.now() - timedelta(days=days)).timestamp())

# ==========================================
# 1. USERS COLLECTION
# ==========================================
def get_user_collection():
    if db is not None: 
        return db['users']
    return None

def create_initial_users():
    users = get_user_collection()
    if users is not None and users.count_documents({}) == 0:
        initial_users = [
            {"username": "op_lina", "password": "123", "role": "Operator", "name": "Lina Operator", "department": "Produksi"},
            {"username": "tech_budi", "password": "123", "role": "Teknisi", "name": "Budi Teknisi", "department": "Maintenance"},
            {"username": "sup_adi", "password": "123", "role": "Supervisor", "name": "Adi Supervisor", "department": "Maintenance"},
            {"username": "mgr_maya", "password": "123", "role": "Manager", "name": "Maya Manager", "department": "Management"}
        ]
        users.insert_many(initial_users)
        print("User awal berhasil dibuat.")

def register_new_user(username, password, role, name, department):
    users = get_user_collection()
    if users is None: 
        return False, "Database tidak terkoneksi"
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
# 2. ASSETS COLLECTION - Data Realistis
# ==========================================
def get_asset_collection():
    if db is not None: 
        return db['assets']
    return None

def create_initial_assets():
    assets = get_asset_collection()
    if assets is not None and assets.count_documents({}) == 0:
        initial_assets = [
            {
                "name": "Mixing Tank A", 
                "location": "Area Pencampuran", 
                "critical_components": MACHINE_COMPONENTS["mixing"],
                "status": "Operasi Normal",
                "type": "mixing",
                "breakdown_count": 2, 
                "last_maintenance": days_ago(15), 
                "efficiency": 85.5,
                "energy_efficiency": 82.0,
                "oee_data": {
                    "availability": 90.5,
                    "performance": 88.2,
                    "quality": 95.1,
                    "oee": 76.8,
                    "calculated_at": days_ago(1)
                },
                "installation_date": days_ago(365),
                "manufacturer": "MixTech Industries",
                "model": "MT-5000"
            },
            {
                "name": "Filling Machine 01", 
                "location": "Lini Pengisian", 
                "critical_components": MACHINE_COMPONENTS["filling"],
                "status": "Operasi Normal",
                "type": "filling",
                "breakdown_count": 1, 
                "last_maintenance": days_ago(30), 
                "efficiency": 92.3,
                "energy_efficiency": 88.5,
                "oee_data": {
                    "availability": 94.2,
                    "performance": 91.8,
                    "quality": 97.5,
                    "oee": 84.3,
                    "calculated_at": days_ago(2)
                },
                "installation_date": days_ago(180),
                "manufacturer": "FillPro Systems",
                "model": "FP-2000"
            },
            {
                "name": "Conveyor Line A", 
                "location": "Lini Pengisian", 
                "critical_components": MACHINE_COMPONENTS["conveyor"],
                "status": "Perlu Perhatian",
                "type": "conveyor",
                "breakdown_count": 4,
                "last_maintenance": days_ago(60), 
                "efficiency": 78.9,
                "energy_efficiency": 75.2,
                "oee_data": {
                    "availability": 85.6,
                    "performance": 82.4,
                    "quality": 92.8,
                    "oee": 65.4,
                    "calculated_at": days_ago(3)
                },
                "installation_date": days_ago(270),
                "manufacturer": "ConveyMax",
                "model": "CM-1500"
            },
            {
                "name": "Labeling Machine B", 
                "location": "Lini Pengemasan", 
                "critical_components": MACHINE_COMPONENTS["labeling"],
                "status": "Operasi Normal",
                "type": "labeling",
                "breakdown_count": 0,
                "last_maintenance": days_ago(10), 
                "efficiency": 95.7,
                "energy_efficiency": 91.3,
                "oee_data": {
                    "availability": 96.8,
                    "performance": 94.2,
                    "quality": 98.5,
                    "oee": 89.8,
                    "calculated_at": days_ago(1)
                },
                "installation_date": days_ago(120),
                "manufacturer": "LabelMaster",
                "model": "LM-3000"
            },
            {
                "name": "Mixing Tank B", 
                "location": "Area Pencampuran", 
                "critical_components": MACHINE_COMPONENTS["mixing"],
                "status": "Bermasalah",
                "type": "mixing",
                "breakdown_count": 6,
                "last_maintenance": days_ago(90), 
                "efficiency": 65.2,
                "energy_efficiency": 62.8,
                "oee_data": {
                    "availability": 72.4,
                    "performance": 68.9,
                    "quality": 85.6,
                    "oee": 42.8,
                    "calculated_at": days_ago(5)
                },
                "installation_date": days_ago(400),
                "manufacturer": "MixTech Industries",
                "model": "MT-5000"
            },
            {
                "name": "Filling Machine 02", 
                "location": "Lini Pengisian", 
                "critical_components": MACHINE_COMPONENTS["filling"],
                "status": "Operasi Normal",
                "type": "filling",
                "breakdown_count": 1,
                "last_maintenance": days_ago(25), 
                "efficiency": 88.4,
                "energy_efficiency": 85.7,
                "oee_data": {
                    "availability": 91.2,
                    "performance": 87.6,
                    "quality": 94.3,
                    "oee": 75.2,
                    "calculated_at": days_ago(2)
                },
                "installation_date": days_ago(200),
                "manufacturer": "FillPro Systems",
                "model": "FP-2000"
            }
        ]
        assets.insert_many(initial_assets)
        print("Aset awal berhasil dibuat.")

# ==========================================
# 3. WORK ORDERS COLLECTION - Kosong Awalnya
# ==========================================
def get_wo_collection():
    if db is not None: 
        return db['work_orders']
    return None

def create_initial_work_orders():
    wo_collection = get_wo_collection()
    if wo_collection is not None and wo_collection.count_documents({}) == 0:
        # Tidak membuat data dummy WO, biarkan kosong
        print("Work Orders collection siap (kosong).")

# ==========================================
# 4. INVENTORY COLLECTION - Data Realistis
# ==========================================
def get_inventory_collection():
    if db is not None: 
        return db['inventory']
    return None

def create_initial_inventory():
    inventory = get_inventory_collection()
    if inventory is not None and inventory.count_documents({}) == 0:
        initial_inventory = []
        
        for machine_type, components in MACHINE_COMPONENTS.items():
            for i, component in enumerate(components):
                # Set stock berbeda untuk simulasi
                current_stock = 50 if i % 2 == 0 else 8
                status = "Aman" if current_stock > 10 else "Rendah"
                
                initial_inventory.append({
                    "item_name": component,
                    "part_number": f"PART-{machine_type.upper()}-{i+1:02d}",
                    "machine_type": machine_type,
                    "current_stock": current_stock,
                    "min_stock": 10,
                    "unit": "pcs",
                    "status": status,
                    "value": 150000,  # Harga realistis
                    "supplier": "PT. Sparepart Indonesia",
                    "location": "Gudang A"
                })
        
        # Tambahkan beberapa item khusus
        special_items = [
            {
                "item_name": "Oil Hydraulic",
                "part_number": "FLUID-HYD-01",
                "machine_type": "general",
                "current_stock": 25,
                "min_stock": 5,
                "unit": "liter",
                "status": "Aman",
                "value": 85000,
                "supplier": "PT. Lubricant Indo",
                "location": "Gudang B"
            },
            {
                "item_name": "V-Belt",
                "part_number": "BELT-V-001",
                "machine_type": "general",
                "current_stock": 6,
                "min_stock": 10,
                "unit": "pcs",
                "status": "Rendah",
                "value": 120000,
                "supplier": "PT. PowerTrans",
                "location": "Gudang A"
            }
        ]
        
        initial_inventory.extend(special_items)
        inventory.insert_many(initial_inventory)
        print("Inventory awal berhasil dibuat.")

# ==========================================
# 5. MAINTENANCE SCHEDULE COLLECTION - Kosong Awalnya
# ==========================================
def get_schedule_collection():
    if db is not None: 
        return db['maintenance_schedule']
    return None

def create_initial_schedule():
    schedule = get_schedule_collection()
    if schedule is not None and schedule.count_documents({}) == 0:
        # Tidak membuat jadwal dummy, biarkan kosong
        print("Maintenance schedule collection siap (kosong).")

# ==========================================
# 6. ENERGY CONSUMPTION COLLECTION - Untuk Fitur Energy Monitoring
# ==========================================
def get_energy_collection():
    if db is not None: 
        return db['energy_consumption']
    return None

def create_initial_energy_data():
    energy_collection = get_energy_collection()
    if energy_collection is not None and energy_collection.count_documents({}) == 0:
        # Data konsumsi energi contoh untuk 7 hari terakhir
        energy_data = []
        current_time = int(time.time())
        
        assets = ["Mixing Tank A", "Filling Machine 01", "Conveyor Line A", "Labeling Machine B"]
        
        for i in range(7):
            day_timestamp = current_time - (i * 24 * 60 * 60)
            for asset in assets:
                # Simulasi data konsumsi energi yang bervariasi
                base_consumption = 150 if "Mixing" in asset else 80
                variation = (i * 5) % 20  # Variasi untuk membuat data lebih realistis
                energy_consumption = base_consumption + variation
                
                energy_data.append({
                    "asset_name": asset,
                    "energy_consumption": energy_consumption,  # kWh
                    "duration_hours": 24,
                    "power_consumption": round(energy_consumption / 24, 2),  # kW
                    "timestamp": day_timestamp,
                    "recorded_by": "system",
                    "recorded_at": day_timestamp
                })
        
        if energy_data:
            energy_collection.insert_many(energy_data)
            print("Data energy consumption awal berhasil dibuat.")

# ==========================================
# 7. MAINTENANCE COSTS COLLECTION - Untuk Fitur Cost Analysis
# ==========================================
def get_maintenance_costs_collection():
    if db is not None: 
        return db['maintenance_costs']
    return None

def create_initial_costs_data():
    costs_collection = get_maintenance_costs_collection()
    if costs_collection is not None and costs_collection.count_documents({}) == 0:
        # Data biaya maintenance contoh untuk 3 bulan terakhir
        costs_data = []
        current_time = int(time.time())
        
        assets = ["Mixing Tank A", "Filling Machine 01", "Conveyor Line A", "Labeling Machine B"]
        cost_types = ["parts", "labor", "downtime", "materials"]
        
        for i in range(90):  # 90 hari terakhir
            day_timestamp = current_time - (i * 24 * 60 * 60)
            
            # Hanya buat data untuk beberapa hari saja (untuk menghindari terlalu banyak data)
            if i % 7 == 0:  # Setiap 7 hari
                for asset in assets:
                    for cost_type in cost_types:
                        # Simulasi biaya yang bervariasi
                        base_amount = 500000 if cost_type == "parts" else 250000
                        variation = (i * 10000) % 100000
                        amount = base_amount + variation
                        
                        costs_data.append({
                            "wo_id": f"WO-{asset.replace(' ', '').upper()}-{i}",
                            "asset_name": asset,
                            "cost_type": cost_type,
                            "amount": amount,
                            "currency": "IDR",
                            "description": f"Biaya {cost_type} untuk maintenance {asset}",
                            "timestamp": day_timestamp,
                            "recorded_by": "system"
                        })
        
        if costs_data:
            costs_collection.insert_many(costs_data)
            print("Data maintenance costs awal berhasil dibuat.")

# ==========================================
# 8. MAINTENANCE BUDGET COLLECTION - Untuk Fitur Budget Tracking
# ==========================================
def get_maintenance_budget_collection():
    if db is not None: 
        return db['maintenance_budget']
    return None

def create_initial_budget_data():
    budget_collection = get_maintenance_budget_collection()
    if budget_collection is not None and budget_collection.count_documents({}) == 0:
        # Data budget untuk tahun berjalan
        current_year = datetime.now().year
        budget_data = []
        
        for quarter in range(1, 5):
            budget_amount = 50000000  # 50 juta per quarter
            
            budget_data.append({
                "year": current_year,
                "quarter": quarter,
                "amount": budget_amount,
                "currency": "IDR",
                "department": "Maintenance",
                "set_by": "system",
                "set_at": int(time.time())
            })
        
        if budget_data:
            budget_collection.insert_many(budget_data)
            print("Data maintenance budget awal berhasil dibuat.")

# ==========================================
# 9. PREDICTIVE MAINTENANCE COLLECTION - Untuk Fitur Predictive Maintenance
# ==========================================
def get_predictive_collection():
    if db is not None: 
        return db['predictive_maintenance']
    return None

def create_initial_predictive_data():
    predictive_collection = get_predictive_collection()
    if predictive_collection is not None and predictive_collection.count_documents({}) == 0:
        # Data predictive maintenance contoh
        predictive_data = [
            {
                "asset_name": "Conveyor Line A",
                "sensor_type": "Vibration",
                "current_value": 7.8,
                "threshold": 8.0,
                "risk_percentage": 97.5,
                "risk_level": "Tinggi",
                "predicted_failure_date": int(time.time()) + (10 * 24 * 60 * 60),  # 10 hari dari sekarang
                "recommended_action": "Perlu inspeksi segera dan penggantian bearing",
                "created_by": "system",
                "created_at": int(time.time()),
                "status": "Aktif"
            },
            {
                "asset_name": "Mixing Tank B",
                "sensor_type": "Temperature",
                "current_value": 85.5,
                "threshold": 90.0,
                "risk_percentage": 95.0,
                "risk_level": "Tinggi",
                "predicted_failure_date": int(time.time()) + (15 * 24 * 60 * 60),  # 15 hari dari sekarang
                "recommended_action": "Monitoring suhu dan cleaning heat exchanger",
                "created_by": "system",
                "created_at": int(time.time()),
                "status": "Aktif"
            },
            {
                "asset_name": "Filling Machine 01",
                "sensor_type": "Pressure",
                "current_value": 12.5,
                "threshold": 15.0,
                "risk_percentage": 83.3,
                "risk_level": "Sedang",
                "predicted_failure_date": int(time.time()) + (30 * 24 * 60 * 60),  # 30 hari dari sekarang
                "recommended_action": "Kalibrasi pressure sensor dan cek seal",
                "created_by": "system",
                "created_at": int(time.time()),
                "status": "Aktif"
            }
        ]
        
        predictive_collection.insert_many(predictive_data)
        print("Data predictive maintenance awal berhasil dibuat.")

# --- Auto Init jika dijalankan langsung ---
if __name__ == '__main__':
    if db is not None:
        create_initial_users()
        create_initial_assets()
        create_initial_inventory()
        create_initial_schedule()
        create_initial_work_orders()
        create_initial_energy_data()
        create_initial_costs_data()
        create_initial_budget_data()
        create_initial_predictive_data()
        print("Database initialized successfully with realistic data for all features!")
    else:
        print("Gagal terhubung ke database, inisialisasi dibatalkan.")