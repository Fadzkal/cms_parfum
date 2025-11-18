from flask import Flask, request, jsonify, redirect, url_for, render_template, session, send_from_directory
from bson.objectid import ObjectId
from functools import wraps
import time
import os
import uuid
import json
from werkzeug.utils import secure_filename
from models import get_user_collection, get_asset_collection, get_wo_collection, get_inventory_collection, get_schedule_collection, register_new_user

app = Flask(__name__)
app.secret_key = 'prime-fragrance-technologies-2024'  # Secret key untuk session

# Konfigurasi file upload (Opsional, jika fitur upload foto digunakan)
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route untuk akses file upload
@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- Dekorator untuk Otorisasi Berdasarkan Role ---
def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session:
                return jsonify({"message": "Silakan login terlebih dahulu"}), 401
                
            user_role = session['user'].get("role")
            if user_role not in allowed_roles:
                return jsonify({"message": f"Akses ditolak. Role {user_role} tidak diizinkan."}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- ROUTING LANDING PAGE & OTENTIKASI (BAGIAN YANG DIUBAH) ---

@app.route('/', methods=['GET'])
def index():
    # Jika user sudah login, langsung arahkan ke dashboard sesuai role
    if 'user' in session:
        role = session['user']['role'].lower()
        return redirect(f'/dashboard/{role}')
    
    # Jika belum login, tampilkan Landing Page
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Scenario 1: Browser meminta halaman Login (GET)
    if request.method == 'GET':
        if 'user' in session:
            role = session['user']['role'].lower()
            return redirect(f'/dashboard/{role}')
        return render_template('login.html')

    # Scenario 2: JavaScript mengirim data login (POST)
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = get_user_collection().find_one({"username": username, "password": password})
    
    if user:
        # Simpan user info di session
        session['user'] = {
            "username": user['username'],
            "role": user['role'],
            "name": user.get('name', user['username']),
            "department": user.get('department', '')
        }
        
        return jsonify({
            "message": "Login berhasil",
            "role": user['role'],
            "username": user['username'],
            "name": user.get('name', user['username']),
            "redirect_url": f"/dashboard/{user['role'].lower()}"
        }), 200
    else:
        return jsonify({"message": "Username atau Password salah"}), 401

@app.route('/logout')
def logout():
    session.pop('user', None)
    # Redirect ke halaman login, bukan landing page, agar flow lebih natural
    return redirect('/login')

@app.route('/api/user-info')
def get_user_info():
    if 'user' in session:
        return jsonify(session['user'])
    return jsonify({"message": "Not logged in"}), 401

# --- ROUTING DASHBOARD ---

@app.route('/dashboard/<role>', methods=['GET'])
def dashboard(role):
    if 'user' not in session:
        return redirect('/login')
    
    if session['user']['role'].lower() != role:
        return jsonify({"message": "Akses tidak diizinkan"}), 403
        
    if role == 'manager':
        return render_template('dashboard_manager.html')
    elif role == 'operator':
        return render_template('dashboard_operator.html')
    elif role == 'teknisi':
        return render_template('dashboard_teknisi.html')
    elif role == 'supervisor':
        return render_template('dashboard_supervisor.html')
    else:
        return "Dashboard tidak ditemukan", 404

# --- ROUTING WORK ORDER (CORE FUNCTIONALITY) ---

# 1. API untuk Operator: Membuat Permintaan WO
@app.route('/api/wo/request', methods=['POST'])
@role_required(["Operator"])
def create_wo_request():
    data = request.get_json()
    asset_name = data.get("asset_id")
    selected_components = data.get("components", [])
    
    # Cari aset berdasarkan nama
    asset = get_asset_collection().find_one({"name": asset_name})
    if not asset:
        return jsonify({"message": f"Aset '{asset_name}' tidak ditemukan."}), 404
    
    # Update breakdown count aset
    get_asset_collection().update_one(
        {"_id": asset['_id']},
        {"$inc": {"breakdown_count": 1}}
    )
        
    wo_data = {
        "asset_id": str(asset['_id']),
        "asset_name": asset_name,
        "asset_type": asset.get('type', ''),
        "description": data.get("description"),
        "components": selected_components, # Sesuai frontend operator
        "type": data.get("wo_type", "Korektif"),
        "priority": data.get("priority", "Sedang"),
        "status": "Baru",
        "requested_by": session['user']['username'],
        "assigned_to": "",
        "timestamp_created": int(time.time()),
        "timestamp_started": None,
        "timestamp_completed": None,
        "completion_notes": "",
        "completion_photos": [], 
        "verified_by": "",
        "timestamp_verified": None,
        "estimated_duration": data.get("estimated_duration", 0),
        "parts_used": []
    }
    
    result = get_wo_collection().insert_one(wo_data)
    return jsonify({"message": "Permintaan WO berhasil dibuat", "wo_id": str(result.inserted_id)}), 201

# 2. API untuk semua role: Melihat WO berdasarkan status
@app.route('/api/wo', methods=['GET'])
@role_required(["Operator", "Teknisi", "Supervisor", "Manager"])
def get_work_orders():
    status_filter = request.args.get('status', '')
    username = session['user']['username']
    user_role = session['user']['role']
    
    query = {}
    
    # Filter berdasarkan role
    if user_role == "Teknisi":
        query["assigned_to"] = username
    elif user_role == "Operator":
        query["requested_by"] = username
    
    # Filter berdasarkan status jika diberikan
    if status_filter:
        query["status"] = status_filter
    
    work_orders = list(get_wo_collection().find(query).sort("timestamp_created", -1))
    
    # Convert ObjectId to string for JSON serialization
    for wo in work_orders:
        wo['_id'] = str(wo['_id'])
        if 'asset_id' in wo:
            wo['asset_id'] = str(wo['asset_id'])
        if 'completion_photos' not in wo:
            wo['completion_photos'] = []
            
    return jsonify(work_orders), 200

# 3. API untuk Supervisor: Melihat WO Baru
@app.route('/api/wo/new', methods=['GET'])
@role_required(["Supervisor"])
def get_new_wo():
    new_wo = list(get_wo_collection().find({"status": "Baru"}).sort("timestamp_created", -1))
    
    for wo in new_wo:
        wo['_id'] = str(wo['_id'])
        if 'asset_id' in wo:
            wo['asset_id'] = str(wo['asset_id'])
        if 'completion_photos' not in wo:
            wo['completion_photos'] = []
            
    return jsonify(new_wo), 200

# 4. API untuk Supervisor: Alokasi WO ke Teknisi
@app.route('/api/wo/assign/<wo_id>', methods=['POST'])
@role_required(["Supervisor"])
def assign_wo(wo_id):
    data = request.get_json()
    technician = data.get("technician")
    
    result = get_wo_collection().update_one(
        {"_id": ObjectId(wo_id)},
        {
            "$set": {
                "status": "Ditugaskan",
                "assigned_to": technician,
                "timestamp_started": int(time.time())
            }
        }
    )
    
    if result.modified_count:
        return jsonify({"message": f"WO berhasil dialokasikan ke {technician}"}), 200
    return jsonify({"message": "WO tidak ditemukan"}), 404

# 5. API untuk Teknisi: Melihat WO yang Ditugaskan
@app.route('/api/wo/assigned', methods=['GET'])
@role_required(["Teknisi"])
def get_assigned_wo():
    username = session['user']['username']
    assigned_wo = list(get_wo_collection().find({
        "assigned_to": username,
        "status": {"$in": ["Ditugaskan", "Dalam Pengerjaan"]}
    }).sort("timestamp_created", -1))
    
    for wo in assigned_wo:
        wo['_id'] = str(wo['_id'])
        if 'asset_id' in wo:
            wo['asset_id'] = str(wo['asset_id'])
        if 'completion_photos' not in wo:
            wo['completion_photos'] = []
            
    return jsonify(assigned_wo), 200

# 6. API untuk Teknisi: Memulai Pengerjaan WO
@app.route('/api/wo/start/<wo_id>', methods=['POST'])
@role_required(["Teknisi"])
def start_wo(wo_id):
    result = get_wo_collection().update_one(
        {"_id": ObjectId(wo_id), "assigned_to": session['user']['username']},
        {"$set": {"status": "Dalam Pengerjaan"}}
    )
    
    if result.modified_count:
        return jsonify({"message": "WO berhasil dimulai"}), 200
    return jsonify({"message": "WO tidak ditemukan"}), 404

# 7. API untuk Teknisi: Menyelesaikan WO (Dengan Upload Foto)
@app.route('/api/wo/complete/<wo_id>', methods=['POST'])
@role_required(["Teknisi"])
def complete_wo(wo_id):
    try:
        # Cek apakah request multipart/form-data (ada file)
        if request.content_type and 'multipart/form-data' in request.content_type:
            notes = request.form.get('notes', '')
            parts_used_json = request.form.get('parts_used', '[]')
            
            photo_paths = []
            if 'photos' in request.files:
                files = request.files.getlist('photos')
                for file in files:
                    if file and file.filename != '' and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        unique_filename = f"{uuid.uuid4().hex}_{filename}"
                        file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                        photo_paths.append(unique_filename)
            
            update_data = {
                "status": "Selesai",
                "timestamp_completed": int(time.time()),
                "completion_notes": notes,
                "parts_used": json.loads(parts_used_json),
                "completion_photos": photo_paths
            }
        else:
            # Fallback JSON Only
            data = request.get_json()
            update_data = {
                "status": "Selesai",
                "timestamp_completed": int(time.time()),
                "completion_notes": data.get("notes", ""),
                "parts_used": data.get("parts_used", []),
                "completion_photos": []
            }

        result = get_wo_collection().update_one(
            {"_id": ObjectId(wo_id), "assigned_to": session['user']['username']},
            {"$set": update_data}
        )
        
        if result.modified_count:
            return jsonify({"message": f"WO {wo_id} berhasil diselesaikan. Menunggu verifikasi."}), 200
        return jsonify({"message": "WO tidak ditemukan atau status tidak sesuai"}), 404

    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

# 8. API untuk Supervisor: Melihat WO Selesai (Perlu Verifikasi)
@app.route('/api/wo/completed', methods=['GET'])
@role_required(["Supervisor"])
def get_completed_wo():
    completed_wo = list(get_wo_collection().find({"status": "Selesai"}).sort("timestamp_completed", -1))
    
    for wo in completed_wo:
        wo['_id'] = str(wo['_id'])
        if 'asset_id' in wo:
            wo['asset_id'] = str(wo['asset_id'])
        if 'completion_photos' not in wo:
            wo['completion_photos'] = []
            
    return jsonify(completed_wo), 200

# 9. API untuk Supervisor: Verifikasi & Tutup WO
@app.route('/api/wo/verify/<wo_id>', methods=['POST'])
@role_required(["Supervisor"])
def verify_wo(wo_id):
    result = get_wo_collection().update_one(
        {"_id": ObjectId(wo_id)},
        {
            "$set": {
                "status": "Ditutup",
                "verified_by": session['user']['username'],
                "timestamp_verified": int(time.time())
            }
        }
    )
    
    if result.modified_count:
        # Update last maintenance timestamp aset
        wo = get_wo_collection().find_one({"_id": ObjectId(wo_id)})
        if wo and 'asset_name' in wo:
            get_asset_collection().update_one(
                {"name": wo['asset_name']},
                {"$set": {"last_maintenance": int(time.time())}}
            )
            
        return jsonify({"message": f"WO {wo_id} berhasil diverifikasi dan ditutup"}), 200
    return jsonify({"message": "WO tidak ditemukan"}), 404

# 10. API untuk mendapatkan detail WO
@app.route('/api/wo/<wo_id>', methods=['GET'])
@role_required(["Operator", "Teknisi", "Supervisor", "Manager"])
def get_wo_detail(wo_id):
    try:
        wo = get_wo_collection().find_one({"_id": ObjectId(wo_id)})
        if wo:
            wo['_id'] = str(wo['_id'])
            if 'asset_id' in wo:
                wo['asset_id'] = str(wo['asset_id'])
            if 'completion_photos' not in wo:
                wo['completion_photos'] = []
            return jsonify(wo), 200
        return jsonify({"message": "WO tidak ditemukan"}), 404
    except:
        return jsonify({"message": "WO ID tidak valid"}), 400

# 11. API untuk Admin/Manager: Registrasi User Baru
@app.route('/api/admin/register', methods=['POST'])
@role_required(["Manager"])
def register_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')
    name = data.get('name')
    department = data.get('department')

    if not all([username, password, role, name, department]):
        return jsonify({"message": "Semua kolom harus diisi."}), 400

    # Panggil fungsi dari models.py
    success, result_message = register_new_user(username, password, role, name, department)

    if success:
        return jsonify({"message": f"Pengguna {username} ({role}) berhasil didaftarkan."}), 201
    else:
        return jsonify({"message": result_message}), 409

# --- ROUTING ASSETS ---

@app.route('/api/assets', methods=['GET'])
@role_required(["Operator", "Supervisor", "Manager", "Teknisi"])
def list_assets():
    assets = list(get_asset_collection().find({}, {"_id": 0, "name": 1, "location": 1, "status": 1, "type": 1}))
    return jsonify(assets), 200

@app.route('/api/assets/detail', methods=['GET'])
@role_required(["Operator", "Supervisor", "Manager", "Teknisi"])
def list_assets_detail():
    assets = list(get_asset_collection().find({}))
    
    for asset in assets:
        asset['_id'] = str(asset['_id'])
        
    return jsonify(assets), 200

@app.route('/api/assets/<asset_name>/components', methods=['GET'])
@role_required(["Operator", "Supervisor", "Teknisi"])
def get_asset_components(asset_name):
    """Mendapatkan daftar komponen untuk aset tertentu"""
    asset = get_asset_collection().find_one({"name": asset_name})
    
    if not asset:
        return jsonify({"message": f"Aset '{asset_name}' tidak ditemukan."}), 404
    
    components = asset.get('critical_components', [])
    return jsonify({
        "asset_name": asset_name,
        "asset_type": asset.get('type', ''),
        "components": components
    }), 200

# --- ROUTING INVENTORY ---

@app.route('/api/inventory', methods=['GET'])
@role_required(["Supervisor", "Manager", "Teknisi"])
def list_inventory():
    inventory = list(get_inventory_collection().find({}))
    
    for item in inventory:
        item['_id'] = str(item['_id'])
        
    return jsonify(inventory), 200

@app.route('/api/inventory/low-stock', methods=['GET'])
@role_required(["Supervisor", "Manager"])
def get_low_stock():
    low_stock = list(get_inventory_collection().find({
        "$expr": {"$lt": ["$current_stock", "$min_stock"]}
    }))
    
    for item in low_stock:
        item['_id'] = str(item['_id'])
        
    return jsonify(low_stock), 200

@app.route('/api/inventory/update/<item_id>', methods=['POST'])
@role_required(["Supervisor"])
def update_inventory(item_id):
    data = request.get_json()
    
    update_data = {}
    if 'current_stock' in data:
        update_data['current_stock'] = data['current_stock']
    if 'min_stock' in data:
        update_data['min_stock'] = data['min_stock']
    
    # Update status berdasarkan stok
    if 'current_stock' in data:
        item = get_inventory_collection().find_one({"_id": ObjectId(item_id)})
        min_stock = data.get('min_stock', item.get('min_stock', 0) if item else 0)
        if data['current_stock'] < min_stock:
            update_data['status'] = 'Rendah'
        else:
            update_data['status'] = 'Aman'
    
    result = get_inventory_collection().update_one(
        {"_id": ObjectId(item_id)},
        {"$set": update_data}
    )
    
    if result.modified_count:
        return jsonify({"message": "Inventory berhasil diupdate"}), 200
    return jsonify({"message": "Item inventory tidak ditemukan"}), 404

# --- ROUTING MAINTENANCE SCHEDULE ---

@app.route('/api/schedule', methods=['GET'])
@role_required(["Operator", "Supervisor", "Manager", "Teknisi"])
def list_schedule():
    schedule = list(get_schedule_collection().find({}).sort("scheduled_date", 1))
    
    for item in schedule:
        item['_id'] = str(item['_id'])
        
    return jsonify(schedule), 200

@app.route('/api/schedule/upcoming', methods=['GET'])
@role_required(["Operator", "Supervisor", "Manager", "Teknisi"])
def get_upcoming_schedule():
    # Jadwal dalam 7 hari ke depan
    seven_days_later = int(time.time()) + (7 * 24 * 60 * 60)
    
    upcoming = list(get_schedule_collection().find({
        "scheduled_date": {"$lte": seven_days_later},
        "status": "Dijadwalkan"
    }).sort("scheduled_date", 1))
    
    for item in upcoming:
        item['_id'] = str(item['_id'])
        
    return jsonify(upcoming), 200

@app.route('/api/schedule/create', methods=['POST'])
@role_required(["Supervisor"])
def create_schedule():
    data = request.get_json()
    
    schedule_data = {
        "asset_name": data.get("asset_name"),
        "type": data.get("type", "Preventif"),
        "description": data.get("description"),
        "scheduled_date": data.get("scheduled_date", int(time.time())),
        "status": "Dijadwalkan",
        "assigned_to": data.get("assigned_to", ""),
        "duration": data.get("duration", 0),
        "created_by": session['user']['username'],
        "created_at": int(time.time())
    }
    
    result = get_schedule_collection().insert_one(schedule_data)
    return jsonify({"message": "Jadwal maintenance berhasil dibuat", "schedule_id": str(result.inserted_id)}), 201

# --- ROUTING MANAGER (KPI Analytics) ---

@app.route('/api/kpi/mttr', methods=['GET'])
@role_required(["Manager"])
def calculate_mttr():
    closed_wo = list(get_wo_collection().find({"status": "Ditutup", "type": "Korektif"}))

    if not closed_wo:
        return jsonify({
            "message": "Tidak ada data WO Korektif yang ditutup untuk dihitung MTTR.",
            "mttr_minutes": 0,
            "total_wo_korektif_closed": 0
        }), 200

    total_repair_time = 0
    count = 0
    
    for wo in closed_wo:
        if wo.get('timestamp_created') and wo.get('timestamp_completed'):
            repair_time = wo['timestamp_completed'] - wo['timestamp_created']
            total_repair_time += repair_time
            count += 1
            
    if count > 0:
        mttr = total_repair_time / count
        return jsonify({
            "message": "MTTR Berhasil Dihitung",
            "total_wo_korektif_closed": count,
            "mttr_seconds": round(mttr, 2),
            "mttr_minutes": round(mttr / 60, 2),
            "mttr_hours": round(mttr / 3600, 2)
        }), 200
    
    return jsonify({"message": "Data WO tidak lengkap untuk perhitungan MTTR"}), 200

@app.route('/api/kpi/assets', methods=['GET'])
@role_required(["Manager"])
def get_asset_kpi():
    assets = list(get_asset_collection().find({}))
    
    # Cari aset dengan breakdown terbanyak
    problem_asset = max(assets, key=lambda x: x.get('breakdown_count', 0)) if assets else None
    
    # Hitung compliance PM
    total_pm = get_wo_collection().count_documents({"type": "Preventif"})
    completed_pm = get_wo_collection().count_documents({"type": "Preventif", "status": "Ditutup"})
    
    pm_compliance = (completed_pm / total_pm * 100) if total_pm > 0 else 0
    
    # Hitung total WO per status
    total_wo = get_wo_collection().count_documents({})
    new_wo = get_wo_collection().count_documents({"status": "Baru"})
    in_progress_wo = get_wo_collection().count_documents({"status": {"$in": ["Ditugaskan", "Dalam Pengerjaan"]}})
    completed_wo = get_wo_collection().count_documents({"status": "Selesai"})
    closed_wo = get_wo_collection().count_documents({"status": "Ditutup"})
    
    return jsonify({
        "problem_asset": problem_asset['name'] if problem_asset else "Tidak ada data",
        "problem_asset_breakdowns": problem_asset['breakdown_count'] if problem_asset else 0,
        "pm_compliance": round(pm_compliance, 1),
        "total_assets": len(assets),
        "wo_stats": {
            "total": total_wo,
            "new": new_wo,
            "in_progress": in_progress_wo,
            "completed": completed_wo,
            "closed": closed_wo
        }
    }), 200

@app.route('/api/kpi/dashboard', methods=['GET'])
@role_required(["Manager"])
def get_dashboard_kpi():
    """KPI lengkap untuk dashboard manager"""
    
    # Data aset
    assets = list(get_asset_collection().find({}))
    total_assets = len(assets)
    operational_assets = len([a for a in assets if a.get('status') == 'Operasi Normal'])
    
    # Data WO
    total_wo = get_wo_collection().count_documents({})
    active_wo = get_wo_collection().count_documents({"status": {"$in": ["Baru", "Ditugaskan", "Dalam Pengerjaan"]}})
    
    # Data inventory
    inventory_items = list(get_inventory_collection().find({}))
    low_stock_items = len([i for i in inventory_items if i.get('status') == 'Rendah'])
    
    # MTTR
    mttr_resp = calculate_mttr()
    mttr_data = mttr_resp.get_json()
    
    return jsonify({
        "total_assets": total_assets,
        "operational_assets": operational_assets,
        "asset_uptime": round((operational_assets / total_assets * 100), 1) if total_assets > 0 else 0,
        "total_work_orders": total_wo,
        "active_work_orders": active_wo,
        "completion_rate": round(((total_wo - active_wo) / total_wo * 100), 1) if total_wo > 0 else 0,
        "low_stock_items": low_stock_items,
        "mttr_minutes": mttr_data.get('mttr_minutes', 0),
        "total_inventory_items": len(inventory_items)
    }), 200

# --- API untuk mendapatkan daftar teknisi ---
@app.route('/api/technicians', methods=['GET'])
@role_required(["Supervisor"])
def get_technicians():
    technicians = list(get_user_collection().find({"role": "Teknisi"}, {"_id": 0, "username": 1, "name": 1}))
    return jsonify(technicians), 200

# --- API untuk mendapatkan statistik role-based ---
@app.route('/api/stats/operator', methods=['GET'])
@role_required(["Operator"])
def get_operator_stats():
    username = session['user']['username']
    
    total_requests = get_wo_collection().count_documents({"requested_by": username})
    pending_requests = get_wo_collection().count_documents({"requested_by": username, "status": "Baru"})
    completed_requests = get_wo_collection().count_documents({"requested_by": username, "status": "Ditutup"})
    
    return jsonify({
        "total_requests": total_requests,
        "pending_requests": pending_requests,
        "completed_requests": completed_requests,
        "completion_rate": round((completed_requests / total_requests * 100), 1) if total_requests > 0 else 0
    }), 200

@app.route('/api/stats/technician', methods=['GET'])
@role_required(["Teknisi"])
def get_technician_stats():
    username = session['user']['username']
    
    assigned_wo = get_wo_collection().count_documents({"assigned_to": username})
    completed_wo = get_wo_collection().count_documents({"assigned_to": username, "status": "Ditutup"})
    in_progress_wo = get_wo_collection().count_documents({"assigned_to": username, "status": {"$in": ["Ditugaskan", "Dalam Pengerjaan"]}})
    
    return jsonify({
        "assigned_work_orders": assigned_wo,
        "completed_work_orders": completed_wo,
        "in_progress_work_orders": in_progress_wo,
        "completion_rate": round((completed_wo / assigned_wo * 100), 1) if assigned_wo > 0 else 0
    }), 200

@app.route('/api/stats/supervisor', methods=['GET'])
@role_required(["Supervisor"])
def get_supervisor_stats():
    new_wo = get_wo_collection().count_documents({"status": "Baru"})
    completed_wo = get_wo_collection().count_documents({"status": "Selesai"})
    assigned_wo = get_wo_collection().count_documents({"status": {"$in": ["Ditugaskan", "Dalam Pengerjaan"]}})
    
    low_stock = get_inventory_collection().count_documents({"status": "Rendah"})
    
    return jsonify({
        "new_work_orders": new_wo,
        "completed_work_orders": completed_wo,
        "assigned_work_orders": assigned_wo,
        "low_stock_items": low_stock,
        "verification_pending": completed_wo
    }), 200

# --- Health Check ---
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": int(time.time()),
        "database": "connected" if get_user_collection() is not None else "disconnected"
    }), 200

# --- Error Handlers ---
@app.errorhandler(404)
def not_found(error):
    return jsonify({"message": "Endpoint tidak ditemukan"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"message": "Terjadi kesalahan internal server"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)