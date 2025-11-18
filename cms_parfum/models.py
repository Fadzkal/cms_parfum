# models.py

from bson.objectid import ObjectId
from db_config import get_db
import time

db = get_db()

# --- Komponen untuk setiap mesin ---
MACHINE_COMPONENTS = {
    "mixing": [
        "Motor Agitator",
        "Agitator Blade / Impeller", 
        "Gearbox / Reducer",
        "Temperature Sensor (Thermocouple/PT100)",
        "Level Sensor",
        "Heating Jacket / Coil",
        "Pressure Relief Valve",
        "Control Panel / PLC Module",
        "Gasket & Seal",
        "Output Valve (Ball Valve / Butterfly Valve)"
    ],
    "filling": [
        "Nozzle Filling",
        "Filling Pump (Piston/Pump/Gravity)",
        "Flow Sensor / Flowmeter", 
        "Hopper / Buffer Tank",
        "Sensor Botol (Photoelectric Sensor)",
        "Solenoid Valve",
        "PLC / Control Board",
        "Pneumatic Cylinder",
        "Tube & Hose Material",
        "Emergency Stop Button (E-Stop)"
    ],
    "conveyor": [
        "Motor Conveyor",
        "Gearbox / Reducer",
        "Conveyor Belt",
        "Roller / Pulley",
        "Frame Body",
        "Sensor Photoelectric", 
        "Control Panel",
        "Inverter (VFD)",
        "Bearing",
        "Emergency Stop Button"
    ],
    "labeling": [
        "Label Dispenser",
        "Label Sensor (Gap Sensor)",
        "Applicator Roller",
        "Bottle Sensor",
        "Stepper Motor",
        "PLC / Controller Unit",
        "Mini Conveyor",
        "Tension Control System",
        "HMI / Touchscreen",
        "Frame & Mounting Bracket"
    ]
}

# --- Koleksi 1: Users ---
def get_user_collection():
    return db['users']

def create_initial_users():
    users = get_user_collection()
    if users.count_documents({}) == 0:
        initial_users = [
            {"username": "op_lina", "password": "123", "role": "Operator", "name": "Lina Operator", "department": "Production"},
            {"username": "tech_budi", "password": "123", "role": "Teknisi", "name": "Budi Teknisi", "department": "Maintenance"},
            {"username": "sup_adi", "password": "123", "role": "Supervisor", "name": "Adi Supervisor", "department": "Maintenance"},
            {"username": "mgr_maya", "password": "123", "role": "Manager", "name": "Maya Manager", "department": "Management"}
        ]
        users.insert_many(initial_users)
        print("User awal berhasil dibuat.")

# --- Koleksi 2: Assets ---
def get_asset_collection():
    return db['assets']

def create_initial_assets():
    assets = get_asset_collection()
    if assets.count_documents({}) == 0:
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

# --- Koleksi 3: Work Orders (WO) ---
def get_wo_collection():
    return db['work_orders']

# --- Koleksi 4: Inventory ---
def get_inventory_collection():
    return db['inventory']

def create_initial_inventory():
    inventory = get_inventory_collection()
    if inventory.count_documents({}) == 0:
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

# --- Koleksi 5: Maintenance Schedule ---
def get_schedule_collection():
    return db['maintenance_schedule']

def create_initial_schedule():
    schedule = get_schedule_collection()
    if schedule.count_documents({}) == 0:
        initial_schedule = [
            {
                "asset_name": "Mixing Tank A",
                "type": "Preventif",
                "description": "Pembersihan dan inspeksi rutin",
                "scheduled_date": int(time.time()) + 86400,
                "status": "Dijadwalkan",
                "assigned_to": "tech_budi",
                "duration": 2
            },
            {
                "asset_name": "Filling Machine 01", 
                "type": "Preventif",
                "description": "Kalibrasi nozzle dan sensor",
                "scheduled_date": int(time.time()) + 172800,
                "status": "Dijadwalkan", 
                "assigned_to": "",
                "duration": 4
            },
            {
                "asset_name": "Conveyor Line A",
                "type": "Preventif", 
                "description": "Pelumasan bearing dan roller",
                "scheduled_date": int(time.time()) + 259200,
                "status": "Dijadwalkan",
                "assigned_to": "",
                "duration": 3
            }
        ]
        schedule.insert_many(initial_schedule)
        print("Jadwal maintenance awal berhasil dibuat.")

# Panggil fungsi inisialisasi
if db is not None:
    create_initial_users()
    create_initial_assets()
    create_initial_inventory()
    create_initial_schedule()