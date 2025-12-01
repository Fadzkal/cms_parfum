# app.py
from flask import Flask, request, jsonify, redirect, url_for, render_template, session, send_from_directory
from flask_cors import CORS 
from bson.objectid import ObjectId
from functools import wraps
import time
import os
import uuid
import json
import math
from werkzeug.utils import secure_filename
from models import get_user_collection, get_asset_collection, get_wo_collection, get_inventory_collection, get_schedule_collection, register_new_user
from datetime import datetime, timedelta 

app = Flask(__name__)
CORS(app) 

app.secret_key = 'prime-fragrance-technologies-2024'  

# Konfigurasi file upload
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 16 * 1024 * 1024 

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database collections untuk fitur baru
def get_energy_collection():
    from models import db
    return db.energy_consumption if db else None

def get_maintenance_costs_collection():
    from models import db
    return db.maintenance_costs if db else None

def get_maintenance_budget_collection():
    from models import db
    return db.maintenance_budget if db else None

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

# Helper function untuk format timestamp
def format_timestamp(ts):
    if ts and ts > 0:
        return datetime.fromtimestamp(ts).strftime('%d %b %Y %H:%M')
    return "N/A"

# --- ROUTING LANDING PAGE & OTENTIKASI ---

@app.route('/', methods=['GET'])
def index():
    if 'user' in session:
        role = session['user']['role'].lower()
        return redirect(f'/dashboard/{role}')
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if 'user' in session:
            role = session['user']['role'].lower()
            return redirect(f'/dashboard/{role}')
        return render_template('login.html')

    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = get_user_collection().find_one({"username": username, "password": password})
    
    if user:
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

# --- ROUTING ADMIN MANAGEMENT ---

@app.route('/api/admin/register', methods=['POST'])
@role_required(["Manager", "Supervisor"])
def register_user():
    """Endpoint untuk mendaftarkan user baru (Manager & Supervisor)"""
    try:
        data = request.get_json()
        
        required_fields = ['name', 'username', 'password', 'role', 'department']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"message": f"Field {field} harus diisi"}), 400
        
        # Validasi role
        allowed_roles = ["Operator", "Teknisi", "Supervisor", "Manager"]
        if data['role'] not in allowed_roles:
            return jsonify({"message": f"Role tidak valid. Pilih dari: {', '.join(allowed_roles)}"}), 400
        
        # Cek apakah username sudah ada
        existing_user = get_user_collection().find_one({"username": data['username']})
        if existing_user:
            return jsonify({"message": "Username sudah terdaftar"}), 400
        
        # Simpan user baru
        user_data = {
            "name": data['name'],
            "username": data['username'],
            "password": data['password'],
            "role": data['role'],
            "department": data['department'],
            "created_at": int(time.time()),
            "created_by": session['user']['username']
        }
        
        result = get_user_collection().insert_one(user_data)
        
        return jsonify({
            "message": f"User {data['name']} berhasil didaftarkan sebagai {data['role']}",
            "user_id": str(result.inserted_id)
        }), 201
        
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route('/api/admin/users', methods=['GET'])
@role_required(["Manager", "Supervisor"])
def get_all_users():
    """Mendapatkan daftar semua user (Manager & Supervisor)"""
    try:
        users = list(get_user_collection().find({}, {"password": 0}).sort("role", 1))
        
        for user in users:
            user['_id'] = str(user['_id'])
            user['created_at_formatted'] = format_timestamp(user.get('created_at'))
            
        return jsonify(users), 200
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

# --- ROUTING WORK ORDER (CORE FUNCTIONALITY) ---

# 1. API untuk Operator: Membuat Permintaan WO dengan Upload Foto
@app.route('/api/wo/request', methods=['POST'])
@role_required(["Operator"])
def create_wo_request():
    try:
        # Handle both JSON and form data
        if request.content_type and 'multipart/form-data' in request.content_type:
            data = request.form
            asset_name = data.get("asset_id")
            selected_components = data.get("components", "").split(",") if data.get("components") else []
        else:
            data = request.get_json()
            asset_name = data.get("asset_id")
            selected_components = data.get("components", [])
        
        asset = get_asset_collection().find_one({"name": asset_name})
        if not asset:
            return jsonify({"message": f"Aset '{asset_name}' tidak ditemukan."}), 404
        
        # Handle photo upload
        photo_paths = []
        if 'photos' in request.files:
            files = request.files.getlist('photos')
            for file in files:
                if file and file.filename != '' and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    unique_filename = f"{uuid.uuid4().hex}_{filename}"
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                    photo_paths.append(unique_filename)
        
        get_asset_collection().update_one(
            {"_id": asset['_id']},
            {"$inc": {"breakdown_count": 1}}
        )
            
        wo_data = {
            "asset_id": str(asset['_id']), 
            "asset_name": asset_name,
            "asset_type": asset.get('type', ''),
            "description": data.get("description"),
            "components": selected_components, 
            "type": data.get("wo_type", "Korektif"),
            "priority": data.get("priority", "Sedang"),
            "status": "Baru",
            "requested_by": session['user']['username'],
            "assigned_to": "",
            
            # Inisialisasi field detail WO
            "technician": "",
            "supervisor": "",
            "root_cause": "",
            "component_failed": "",

            "timestamp_created": int(time.time()),
            "timestamp_started": None,
            "timestamp_completed": None,
            "completion_notes": "",
            "completion_photos": photo_paths,  # Save uploaded photos
            "verified_by": "",
            "timestamp_verified": None,
            "estimated_duration": data.get("estimated_duration", 0),
            "parts_used": []
        }
        
        result = get_wo_collection().insert_one(wo_data)
        return jsonify({
            "message": "Permintaan WO berhasil dibuat", 
            "wo_id": str(result.inserted_id),
            "photo_count": len(photo_paths)
        }), 201
        
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

# 2. API untuk upload foto tambahan ke WO yang sudah ada
@app.route('/api/wo/<wo_id>/upload-photos', methods=['POST'])
@role_required(["Operator", "Teknisi"])
def upload_wo_photos(wo_id):
    try:
        if 'photos' not in request.files:
            return jsonify({"message": "Tidak ada file yang diupload"}), 400
            
        files = request.files.getlist('photos')
        photo_paths = []
        
        for file in files:
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                photo_paths.append(unique_filename)
        
        if photo_paths:
            # Update WO dengan foto baru
            result = get_wo_collection().update_one(
                {"_id": ObjectId(wo_id)},
                {"$push": {"completion_photos": {"$each": photo_paths}}}
            )
            
            if result.modified_count:
                return jsonify({
                    "message": f"{len(photo_paths)} foto berhasil diupload",
                    "photo_urls": photo_paths
                }), 200
            else:
                return jsonify({"message": "WO tidak ditemukan"}), 404
        else:
            return jsonify({"message": "Tidak ada file valid yang diupload"}), 400
            
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

# 3. API untuk semua role: Melihat WO berdasarkan status
@app.route('/api/wo', methods=['GET'])
@role_required(["Operator", "Teknisi", "Supervisor", "Manager"])
def get_work_orders():
    status_filter = request.args.get('status', '')
    username = session['user']['username']
    user_role = session['user']['role']
    
    query = {}
    
    if user_role == "Teknisi":
        query["assigned_to"] = username
    elif user_role == "Operator":
        query["requested_by"] = username
    
    if status_filter:
        query["status"] = status_filter
    
    work_orders = list(get_wo_collection().find(query).sort("timestamp_created", -1))
    
    for wo in work_orders:
        wo['_id'] = str(wo['_id'])
        if 'asset_id' in wo:
            wo['asset_id'] = str(wo['_id'])
        if 'completion_photos' not in wo:
            wo['completion_photos'] = []
        if 'photos' not in wo:
            wo['photos'] = []
            
    return jsonify(work_orders), 200

# 4. API untuk Supervisor: Melihat WO Baru
@app.route('/api/wo/new', methods=['GET'])
@role_required(["Supervisor"])
def get_new_wo():
    new_wo = list(get_wo_collection().find({"status": "Baru"}).sort("timestamp_created", -1))
    
    for wo in new_wo:
        wo['_id'] = str(wo['_id'])
        if 'asset_id' in wo:
            wo['asset_id'] = str(wo['_id'])
        if 'completion_photos' not in wo:
            wo['completion_photos'] = []
        if 'photos' not in wo:
            wo['photos'] = []
            
    return jsonify(new_wo), 200

# 5. API untuk Supervisor: Alokasi WO ke Teknisi
@app.route('/api/wo/assign/<wo_id>', methods=['POST'])
@role_required(["Supervisor"])
def assign_wo(wo_id):
    data = request.get_json()
    technician_username = data.get("technician")
    
    # Ambil nama lengkap teknisi dari koleksi users
    user = get_user_collection().find_one({"username": technician_username})
    technician_name = user.get('name') if user else technician_username

    result = get_wo_collection().update_one(
        {"_id": ObjectId(wo_id)},
        {
            "$set": {
                "status": "Ditugaskan",
                "assigned_to": technician_username,
                "technician": technician_name,
                "timestamp_started": int(time.time())
            }
        }
    )
    
    if result.modified_count:
        return jsonify({"message": f"WO berhasil dialokasikan ke {technician_name}"}), 200
    return jsonify({"message": "WO tidak ditemukan"}), 404

# 6. API untuk Teknisi: Melihat WO yang Ditugaskan
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
            wo['asset_id'] = str(wo['_id'])
        if 'completion_photos' not in wo:
            wo['completion_photos'] = []
        if 'photos' not in wo:
            wo['photos'] = []
            
    return jsonify(assigned_wo), 200

# 7. API untuk Teknisi: Memulai Pengerjaan WO
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

# 8. API untuk Teknisi: Menyelesaikan WO
@app.route('/api/wo/complete/<wo_id>', methods=['POST'])
@role_required(["Teknisi"])
def complete_wo(wo_id):
    try:
        data = request.form if request.content_type and 'multipart/form-data' in request.content_type else request.get_json()
        
        root_cause = data.get('root_cause', 'Data belum diisi')
        component_failed = data.get('component_failed', 'Data belum diisi')
        
        # Handle photo upload for completion
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
            "completion_notes": data.get("notes", ""),
            "parts_used": json.loads(data.get("parts_used", '[]')) if isinstance(data.get("parts_used"), str) else data.get("parts_used", []),
            "completion_photos": photo_paths,
            "root_cause": root_cause,
            "component_failed": component_failed,
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

# 9. API untuk Supervisor: Melihat WO Selesai
@app.route('/api/wo/completed', methods=['GET'])
@role_required(["Supervisor"])
def get_completed_wo():
    completed_wo = list(get_wo_collection().find({"status": "Selesai"}).sort("timestamp_completed", -1))
    
    for wo in completed_wo:
        wo['_id'] = str(wo['_id'])
        if 'asset_id' in wo:
            wo['asset_id'] = str(wo['_id'])
        if 'completion_photos' not in wo:
            wo['completion_photos'] = []
        if 'photos' not in wo:
            wo['photos'] = []
            
    return jsonify(completed_wo), 200

# 10. API untuk Supervisor: Verifikasi & Tutup WO
@app.route('/api/wo/verify/<wo_id>', methods=['POST'])
@role_required(["Supervisor"])
def verify_wo(wo_id):
    supervisor_name = session['user'].get('name', session['user']['username'])

    result = get_wo_collection().update_one(
        {"_id": ObjectId(wo_id)},
        {
            "$set": {
                "status": "Ditutup",
                "verified_by": session['user']['username'],
                "supervisor": supervisor_name,
                "timestamp_verified": int(time.time())
            }
        }
    )
    
    if result.modified_count:
        wo = get_wo_collection().find_one({"_id": ObjectId(wo_id)})
        if wo and 'asset_name' in wo:
            get_asset_collection().update_one(
                {"name": wo['asset_name']},
                {"$set": {"last_maintenance": int(time.time())}}
            )
            
        return jsonify({"message": f"WO {wo_id} berhasil diverifikasi dan ditutup"}), 200
    return jsonify({"message": "WO tidak ditemukan"}), 404

# 11. API untuk mendapatkan detail WO
@app.route('/api/wo/<wo_id>', methods=['GET'])
@role_required(["Operator", "Teknisi", "Supervisor", "Manager"])
def get_wo_detail(wo_id):
    try:
        wo = get_wo_collection().find_one({"_id": ObjectId(wo_id)})
        if wo:
            wo['_id'] = str(wo['_id'])
            if 'asset_id' in wo:
                wo['asset_id'] = str(wo['_id'])
            if 'completion_photos' not in wo:
                wo['completion_photos'] = []
            if 'photos' not in wo:
                wo['photos'] = []
            return jsonify(wo), 200
        return jsonify({"message": "WO tidak ditemukan"}), 404
    except:
        return jsonify({"message": "WO ID tidak valid"}), 400

# --- ROUTING ASSETS ---

@app.route('/api/assets', methods=['GET'])
@role_required(["Operator", "Supervisor", "Manager", "Teknisi"])
def list_assets():
    assets = list(get_asset_collection().find({}, {"_id": 0, "name": 1, "location": 1, "status": 1, "type": 1}))
    return jsonify(assets), 200

@app.route('/api/assets/detail', methods=['GET']) 
@role_required(["Operator", "Supervisor", "Manager", "Teknisi"])
def list_assets_detail():
    assets_cursor = get_asset_collection().find({})
    asset_list = []
    
    for asset in assets_cursor:
        asset_list.append({
            "name": asset.get("name"),
            "location": asset.get("location"),
            "status": asset.get("status"), 
            "breakdown_count": asset.get("breakdown_count", 0),
            "efficiency": asset.get("efficiency", 0)
        })
        
    return jsonify(asset_list), 200

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

# API untuk menambah aset baru
@app.route('/api/assets/create', methods=['POST'])
@role_required(["Manager", "Supervisor"])
def create_asset():
    try:
        data = request.get_json()
        
        # Validasi data
        required_fields = ['name', 'location', 'type', 'status']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"message": f"Field {field} harus diisi"}), 400
        
        # Cek apakah aset sudah ada
        existing_asset = get_asset_collection().find_one({"name": data['name']})
        if existing_asset:
            return jsonify({"message": f"Aset dengan nama {data['name']} sudah ada"}), 400
        
        asset_data = {
            "name": data['name'],
            "location": data['location'],
            "type": data['type'],
            "status": data['status'],
            "critical_components": data.get('critical_components', []),
            "breakdown_count": 0,
            "efficiency": 0,
            "installation_date": int(time.time()),
            "last_maintenance": None,
            "manufacturer": data.get('manufacturer', ''),
            "model": data.get('model', ''),
            "created_by": session['user']['username'],
            "created_at": int(time.time())
        }
        
        result = get_asset_collection().insert_one(asset_data)
        
        return jsonify({
            "message": f"Aset {data['name']} berhasil didaftarkan",
            "asset_id": str(result.inserted_id)
        }), 201
        
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

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

# --- ROUTING MAINTENANCE SCHEDULE (DIPERBAIKI) ---

@app.route('/api/schedule', methods=['GET'])
@role_required(["Operator", "Supervisor", "Manager", "Teknisi"])
def list_schedule():
    """Mendapatkan semua jadwal maintenance"""
    try:
        user_role = session['user']['role']
        username = session['user']['username']
        
        query = {}
        
        # Teknisi hanya melihat jadwal yang ditugaskan ke mereka
        if user_role == "Teknisi":
            query["$or"] = [
                {"assigned_to": username},
                {"assigned_to": ""},  # Jadwal tanpa teknisi tertentu
                {"assigned_to": {"$exists": False}}
            ]
        
        schedule = list(get_schedule_collection().find(query).sort("scheduled_date", 1))
        
        for item in schedule:
            item['_id'] = str(item['_id'])
            # Format tanggal untuk frontend
            if item.get('scheduled_date'):
                item['scheduled_date_formatted'] = format_timestamp(item['scheduled_date'])
            
        return jsonify(schedule), 200
        
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route('/api/schedule/upcoming', methods=['GET'])
@role_required(["Operator", "Supervisor", "Manager", "Teknisi"])
def get_upcoming_schedule():
    """Mendapatkan jadwal yang akan datang (7 hari ke depan)"""
    try:
        seven_days_later = int(time.time()) + (7 * 24 * 60 * 60)
        current_time = int(time.time())
        
        user_role = session['user']['role']
        username = session['user']['username']
        
        query = {
            "scheduled_date": {"$gte": current_time, "$lte": seven_days_later},
            "status": "Dijadwalkan"
        }
        
        # Filter untuk teknisi
        if user_role == "Teknisi":
            query["$or"] = [
                {"assigned_to": username},
                {"assigned_to": ""},
                {"assigned_to": {"$exists": False}}
            ]
        
        upcoming = list(get_schedule_collection().find(query).sort("scheduled_date", 1))
        
        for item in upcoming:
            item['_id'] = str(item['_id'])
            if item.get('scheduled_date'):
                item['scheduled_date_formatted'] = format_timestamp(item['scheduled_date'])
                # Calculate days until schedule
                days_until = (item['scheduled_date'] - current_time) / (24 * 60 * 60)
                item['days_until'] = math.ceil(days_until)
            
        return jsonify(upcoming), 200
        
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route('/api/schedule/create', methods=['POST'])
@role_required(["Supervisor", "Manager"])
def create_schedule():
    """Membuat jadwal maintenance baru"""
    try:
        data = request.get_json()
        
        # Validasi data
        required_fields = ['asset_name', 'type', 'description', 'scheduled_date']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"message": f"Field {field} harus diisi"}), 400
        
        schedule_data = {
            "asset_name": data['asset_name'],
            "type": data['type'],
            "description": data['description'],
            "scheduled_date": data['scheduled_date'],
            "duration": data.get('duration', 60),
            "priority": data.get('priority', 'Sedang'),
            "status": "Dijadwalkan",
            "assigned_to": data.get('assigned_to', ''),  # Bisa kosong untuk semua teknisi
            "created_by": session['user']['username'],
            "created_at": int(time.time()),
            "notes": "",
            "completed_by": "",
            "completed_at": None
        }
        
        result = get_schedule_collection().insert_one(schedule_data)
        
        return jsonify({
            "message": "Jadwal maintenance berhasil dibuat", 
            "schedule_id": str(result.inserted_id)
        }), 201
        
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route('/api/schedule/update/<schedule_id>', methods=['POST'])
@role_required(["Supervisor", "Teknisi"])
def update_schedule(schedule_id):
    """Update status jadwal maintenance"""
    try:
        data = request.get_json()
        
        update_data = {}
        if 'status' in data:
            update_data['status'] = data['status']
        if 'notes' in data:
            update_data['notes'] = data['notes']
        if 'completed_by' in data:
            update_data['completed_by'] = data['completed_by']
        
        if 'status' in data and data['status'] == 'Selesai':
            update_data['completed_at'] = int(time.time())
            if 'completed_by' not in update_data:
                update_data['completed_by'] = session['user']['username']
        
        result = get_schedule_collection().update_one(
            {"_id": ObjectId(schedule_id)},
            {"$set": update_data}
        )
        
        if result.modified_count:
            return jsonify({"message": "Jadwal berhasil diupdate"}), 200
        return jsonify({"message": "Jadwal tidak ditemukan"}), 404
        
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route('/api/schedule/technician', methods=['GET'])
@role_required(["Teknisi"])
def get_technician_schedule():
    """Mendapatkan jadwal khusus untuk teknisi yang login"""
    try:
        username = session['user']['username']
        
        # Jadwal yang ditugaskan ke teknisi ini ATAU tanpa penugasan spesifik
        schedules = list(get_schedule_collection().find({
            "$or": [
                {"assigned_to": username},
                {"assigned_to": ""},
                {"assigned_to": {"$exists": False}}
            ],
            "status": {"$in": ["Dijadwalkan", "Dalam Pengerjaan"]}
        }).sort("scheduled_date", 1))
        
        for schedule in schedules:
            schedule['_id'] = str(schedule['_id'])
            if schedule.get('scheduled_date'):
                schedule['scheduled_date_formatted'] = format_timestamp(schedule['scheduled_date'])
                # Hitung hari menuju jadwal
                days_until = (schedule['scheduled_date'] - int(time.time())) / (24 * 60 * 60)
                schedule['days_until'] = math.ceil(days_until)
            
        return jsonify(schedules), 200
        
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

# --- HELPER FUNCTION UNTUK MTTR ---
def mttr_calculator():
    wo_collection = get_wo_collection()
    closed_wo = list(wo_collection.find({"status": "Ditutup", "type": "Korektif"}))

    total_repair_time_seconds = 0
    count = 0
    
    for wo in closed_wo:
        created = wo.get('timestamp_created')
        completed = wo.get('timestamp_completed')
        
        if created and completed:
            repair_time = completed - created
            total_repair_time_seconds += repair_time
            count += 1
            
    mttr_minutes = 0.0
    if count > 0:
        mttr_minutes = round((total_repair_time_seconds / 60) / count, 1) 
        
    return {
        "mttr_minutes": mttr_minutes,
        "total_wo_korektif_closed": count
    }

# --- ROUTING MANAGER (KPI Analytics) ---

@app.route('/api/kpi/mttr', methods=['GET'])
@role_required(["Manager"])
def calculate_mttr_api():
    mttr_data = mttr_calculator()
    return jsonify({
        "message": "MTTR Berhasil Dihitung",
        "total_wo_korektif_closed": mttr_data['total_wo_korektif_closed'],
        "mttr_seconds": round(mttr_data['mttr_minutes'] * 60, 2),
        "mttr_minutes": mttr_data['mttr_minutes'],
        "mttr_hours": round(mttr_data['mttr_minutes'] / 60, 2)
    }), 200

@app.route('/api/kpi/assets', methods=['GET'])
@role_required(["Manager"])
def get_asset_kpi():
    asset_collection = get_asset_collection()
    wo_collection = get_wo_collection()
    
    if asset_collection is None or wo_collection is None:
        return jsonify({"message": "Database not connected"}), 500

    problem_asset_count = asset_collection.count_documents({"status": "Bermasalah"})
    
    total_pm_wo = wo_collection.count_documents({"type": "Preventif"})
    completed_pm_wo = wo_collection.count_documents({"type": "Preventif", "status": "Ditutup"})
    
    pm_compliance = (completed_pm_wo / total_pm_wo * 100) if total_pm_wo > 0 else 0
    
    new_wo = wo_collection.count_documents({"status": "Baru"})
    in_progress_wo = wo_collection.count_documents({"status": {"$in": ["Ditugaskan", "Dalam Pengerjaan"]}})
    completed_wo = wo_collection.count_documents({"status": "Selesai"})
    closed_wo = wo_collection.count_documents({"status": "Ditutup"})
    
    return jsonify({
        "problem_asset": problem_asset_count, 
        "pm_compliance": round(pm_compliance, 1),
        "wo_stats": { 
            "new": new_wo,
            "in_progress": in_progress_wo,
            "completed": completed_wo,
            "closed": closed_wo
        }
    }), 200

@app.route('/api/kpi/dashboard', methods=['GET'])
@role_required(["Manager"])
def get_dashboard_kpi():
    asset_collection = get_asset_collection()
    wo_collection = get_wo_collection()
    
    if asset_collection is None or wo_collection is None:
        return jsonify({"message": "Database not connected"}), 500
        
    total_assets = asset_collection.count_documents({})
    operational_assets = asset_collection.count_documents({"status": {"$in": ["Operasi Normal", "Perlu Perhatian"]}}) 
    
    active_wo = wo_collection.count_documents({"status": {"$in": ["Baru", "Ditugaskan", "Dalam Pengerjaan"]}})
    
    mttr_data = mttr_calculator()
    
    return jsonify({
        "total_assets": total_assets,
        "operational_assets": operational_assets,
        "asset_uptime": round((operational_assets / total_assets * 100), 1) if total_assets > 0 else 0,
        "total_work_orders": wo_collection.count_documents({}),
        "active_work_orders": active_wo, 
        "completion_rate": 0, 
        "low_stock_items": 0, 
        "mttr_minutes": mttr_data['mttr_minutes'], 
        "total_inventory_items": 0 
    }), 200

# =========================================================
# ENDPOINT 12: FULL WORK ORDER HISTORY (DIPERBAIKI)
# =========================================================
@app.route('/api/work_orders/history', methods=['GET'])
@role_required(["Supervisor", "Manager", "Teknisi"])
def get_work_order_history():
    wo_collection = get_wo_collection()
    if wo_collection is None:
        return jsonify({"message": "Database error"}), 500

    work_orders = list(wo_collection.find().sort("timestamp_created", -1))

    result = []
    for wo in work_orders:
        repair_duration = "N/A"
        
        # Hitung durasi perbaikan menggunakan timestamp_completed dan timestamp_created
        if wo.get("timestamp_created") and wo.get("timestamp_completed"):
            start = wo["timestamp_created"] # Mulai hitung dari WO dibuat
            end = wo["timestamp_completed"]
            duration_sec = end - start
            
            if duration_sec > 0:
                hours = int(duration_sec // 3600)
                minutes = int((duration_sec % 3600) // 60)
                repair_duration = f"{hours}j {minutes}m"
        
        # Ambil nama teknisi/supervisor. Gunakan nilai yang diset manual di models.py/verify_wo sebagai prioritas
        technician_name = wo.get("technician") or wo.get("assigned_to") or "N/A"
        supervisor_name = wo.get("supervisor") or "N/A"

        result.append({
            "id": str(wo.get("_id")),
            "asset_name": wo.get("asset_name"),
            "type": wo.get("type"),
            "priority": wo.get("priority"),
            "status": wo.get("status"),
            
            # Detail Teknis & Pelaksana
            "technician": technician_name, 
            "supervisor": supervisor_name,
            "root_cause": wo.get("root_cause", "N/A"),
            "component_failed": wo.get("component_failed", "N/A"),
            
            # Detail Waktu
            "requested_at": format_timestamp(wo.get("timestamp_created")),
            "repair_start": format_timestamp(wo.get("timestamp_started")), # Menggunakan timestamp_started
            "completed_at": format_timestamp(wo.get("timestamp_completed")),
            "duration": repair_duration, # Hasil perhitungan
        })

    return jsonify(result)
# --- END WO HISTORY ---

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

# --- ROUTING MAINTENANCE SCHEDULE FOR OPERATOR ---

@app.route('/api/schedule/operator', methods=['GET'])
@role_required(["Operator"])
def get_operator_schedule():
    """Mendapatkan jadwal maintenance untuk operator"""
    try:
        # Get upcoming schedules (next 30 days)
        thirty_days_later = int(time.time()) + (30 * 24 * 60 * 60)
        
        schedules = list(get_schedule_collection().find({
            "scheduled_date": {"$lte": thirty_days_later},
            "status": {"$in": ["Dijadwalkan", "Dalam Pengerjaan"]}
        }).sort("scheduled_date", 1))
        
        for schedule in schedules:
            schedule['_id'] = str(schedule['_id'])
            # Format tanggal untuk display
            if schedule.get('scheduled_date'):
                schedule['scheduled_date_formatted'] = format_timestamp(schedule['scheduled_date'])
            
        return jsonify(schedules), 200
        
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route('/api/schedule/notify-operator', methods=['POST'])
@role_required(["Supervisor", "Manager"])
def notify_operator_schedule():
    """Mengirim notifikasi jadwal maintenance ke operator"""
    try:
        data = request.get_json()
        schedule_id = data.get('schedule_id')
        message = data.get('message', 'Jadwal maintenance baru telah ditambahkan')
        
        # Di production, ini bisa integrate dengan email/WhatsApp
        # Untuk sekarang kita simpan di database sebagai notification
        schedule = get_schedule_collection().find_one({"_id": ObjectId(schedule_id)})
        
        if schedule:
            return jsonify({
                "message": "Notifikasi berhasil dikirim",
                "schedule": schedule.get('asset_name'),
                "scheduled_date": format_timestamp(schedule.get('scheduled_date'))
            }), 200
        else:
            return jsonify({"message": "Jadwal tidak ditemukan"}), 404
            
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route('/api/schedule/operator-upcoming', methods=['GET'])
@role_required(["Operator"])
def get_operator_upcoming_schedule():
    """Mendapatkan jadwal maintenance yang akan datang untuk operator"""
    try:
        # Get schedules for next 7 days
        seven_days_later = int(time.time()) + (7 * 24 * 60 * 60)
        current_time = int(time.time())
        
        schedules = list(get_schedule_collection().find({
            "scheduled_date": {"$gte": current_time, "$lte": seven_days_later},
            "status": "Dijadwalkan"
        }).sort("scheduled_date", 1))
        
        for schedule in schedules:
            schedule['_id'] = str(schedule['_id'])
            if schedule.get('scheduled_date'):
                schedule['scheduled_date_formatted'] = format_timestamp(schedule['scheduled_date'])
                # Calculate days until schedule
                days_until = (schedule['scheduled_date'] - current_time) / (24 * 60 * 60)
                schedule['days_until'] = math.ceil(days_until)
            
        return jsonify(schedules), 200
        
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

# =========================================================
# FITUR 1: OEE (Overall Equipment Effectiveness)
# =========================================================

@app.route('/api/oee/calculate', methods=['POST'])
@role_required(["Manager", "Supervisor"])
def calculate_oee():
    """Menghitung OEE untuk mesin tertentu"""
    try:
        data = request.get_json()
        
        required_fields = ['asset_name', 'planned_production_time', 'actual_production_time', 
                          'ideal_cycle_time', 'total_units', 'good_units']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"message": f"Field {field} harus diisi"}), 400
        
        # Calculate OEE components
        # Availability
        availability = (data['actual_production_time'] / data['planned_production_time']) * 100
        
        # Performance
        expected_units = data['actual_production_time'] / data['ideal_cycle_time']
        performance = (data['total_units'] / expected_units) * 100 if expected_units > 0 else 0
        
        # Quality
        quality = (data['good_units'] / data['total_units']) * 100 if data['total_units'] > 0 else 0
        
        # Overall OEE
        oee = (availability * performance * quality) / 10000  # Convert from percentage
        
        # Save OEE data to asset
        asset = get_asset_collection().find_one({"name": data['asset_name']})
        if asset:
            get_asset_collection().update_one(
                {"_id": asset['_id']},
                {"$set": {
                    "oee_data": {
                        "availability": round(availability, 2),
                        "performance": round(performance, 2),
                        "quality": round(quality, 2),
                        "oee": round(oee, 2),
                        "calculated_at": int(time.time())
                    },
                    "efficiency": round(oee, 1)
                }}
            )
        
        return jsonify({
            "availability": round(availability, 2),
            "performance": round(performance, 2),
            "quality": round(quality, 2),
            "oee": round(oee, 2),
            "message": "OEE berhasil dihitung"
        }), 200
        
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route('/api/oee/assets', methods=['GET'])
@role_required(["Manager", "Supervisor"])
def get_assets_oee():
    """Mendapatkan data OEE semua aset"""
    try:
        assets = list(get_asset_collection().find({}))
        
        oee_data = []
        for asset in assets:
            asset_oee = {
                "asset_name": asset.get("name"),
                "asset_type": asset.get("type"),
                "location": asset.get("location"),
                "status": asset.get("status"),
                "efficiency": asset.get("efficiency", 0),
                "oee_data": asset.get("oee_data", {})
            }
            oee_data.append(asset_oee)
            
        return jsonify(oee_data), 200
        
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

# =========================================================
# FITUR 2: Predictive Maintenance
# =========================================================

@app.route('/api/predictive/maintenance', methods=['POST'])
@role_required(["Manager", "Supervisor"])
def create_predictive_maintenance():
    """Membuat jadwal predictive maintenance berdasarkan data sensor"""
    try:
        data = request.get_json()
        
        required_fields = ['asset_name', 'sensor_type', 'current_value', 'threshold', 'predicted_failure_date']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"message": f"Field {field} harus diisi"}), 400
        
        # Calculate risk level
        risk_percentage = (data['current_value'] / data['threshold']) * 100
        risk_level = "Rendah"
        if risk_percentage >= 80:
            risk_level = "Tinggi"
        elif risk_percentage >= 60:
            risk_level = "Sedang"
        
        predictive_data = {
            "asset_name": data['asset_name'],
            "sensor_type": data['sensor_type'],
            "current_value": data['current_value'],
            "threshold": data['threshold'],
            "risk_percentage": round(risk_percentage, 2),
            "risk_level": risk_level,
            "predicted_failure_date": data['predicted_failure_date'],
            "recommended_action": data.get('recommended_action', 'Monitoring dan inspeksi rutin'),
            "created_by": session['user']['username'],
            "created_at": int(time.time()),
            "status": "Aktif"
        }
        
        result = get_schedule_collection().insert_one(predictive_data)
        
        # Also create a maintenance schedule
        schedule_data = {
            "asset_name": data['asset_name'],
            "type": "Predictive",
            "description": f"Predictive maintenance berdasarkan sensor {data['sensor_type']}. Risk: {risk_level} ({risk_percentage}%)",
            "scheduled_date": data['predicted_failure_date'] - (7 * 24 * 60 * 60),  # 1 week before predicted failure
            "duration": 120,
            "priority": "Tinggi" if risk_level == "Tinggi" else "Sedang",
            "status": "Dijadwalkan",
            "created_by": session['user']['username'],
            "created_at": int(time.time()),
            "predictive_maintenance_id": str(result.inserted_id)
        }
        
        get_schedule_collection().insert_one(schedule_data)
        
        return jsonify({
            "message": f"Predictive maintenance berhasil dibuat. Level risiko: {risk_level}",
            "risk_level": risk_level,
            "risk_percentage": risk_percentage,
            "schedule_id": str(result.inserted_id)
        }), 201
        
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route('/api/predictive/risk-assessment', methods=['GET'])
@role_required(["Manager", "Supervisor"])
def get_risk_assessment():
    """Mendapatkan assessment risiko untuk semua aset"""
    try:
        # Get assets with high breakdown count
        assets = list(get_asset_collection().find({"breakdown_count": {"$gt": 0}}).sort("breakdown_count", -1))
        
        risk_assessment = []
        for asset in assets:
            breakdown_count = asset.get('breakdown_count', 0)
            
            # Calculate risk based on breakdown frequency
            if breakdown_count >= 5:
                risk_level = "Tinggi"
                recommendation = "Perlu preventive maintenance segera dan evaluasi mendalam"
            elif breakdown_count >= 3:
                risk_level = "Sedang" 
                recommendation = "Perlu penjadwalan preventive maintenance"
            else:
                risk_level = "Rendah"
                recommendation = "Monitoring rutin"
            
            risk_assessment.append({
                "asset_name": asset.get('name'),
                "asset_type": asset.get('type'),
                "breakdown_count": breakdown_count,
                "last_maintenance": format_timestamp(asset.get('last_maintenance')),
                "risk_level": risk_level,
                "recommendation": recommendation,
                "efficiency": asset.get('efficiency', 0)
            })
        
        return jsonify(risk_assessment), 200
        
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

# =========================================================
# FITUR 3: Energy Monitoring
# =========================================================

@app.route('/api/energy/consumption', methods=['POST'])
@role_required(["Manager", "Supervisor"])
def record_energy_consumption():
    """Mencatat konsumsi energi untuk aset"""
    try:
        data = request.get_json()
        
        required_fields = ['asset_name', 'energy_consumption', 'duration_hours', 'timestamp']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"message": f"Field {field} harus diisi"}), 400
        
        energy_data = {
            "asset_name": data['asset_name'],
            "energy_consumption": data['energy_consumption'],  # in kWh
            "duration_hours": data['duration_hours'],
            "power_consumption": data['energy_consumption'] / data['duration_hours'],  # kW
            "timestamp": data['timestamp'],
            "recorded_by": session['user']['username'],
            "recorded_at": int(time.time())
        }
        
        # Simpan ke collection terpisah untuk energy monitoring
        energy_collection = get_energy_collection()
        if energy_collection is None:
            return jsonify({"message": "Database energy collection tidak tersedia"}), 500
            
        result = energy_collection.insert_one(energy_data)
        
        # Update efficiency score based on energy consumption
        asset = get_asset_collection().find_one({"name": data['asset_name']})
        if asset:
            # Simple efficiency calculation based on energy consumption
            # Lower energy consumption per hour = higher efficiency
            optimal_consumption = 10  # kW - adjust based on your standards
            current_consumption = energy_data['power_consumption']
            
            if current_consumption <= optimal_consumption:
                energy_efficiency = 95
            else:
                energy_efficiency = max(50, 95 - ((current_consumption - optimal_consumption) * 5))
            
            get_asset_collection().update_one(
                {"_id": asset['_id']},
                {"$set": {
                    "energy_efficiency": round(energy_efficiency, 1),
                    "last_energy_record": int(time.time())
                }}
            )
        
        return jsonify({
            "message": "Data konsumsi energi berhasil dicatat",
            "energy_id": str(result.inserted_id),
            "power_consumption": round(energy_data['power_consumption'], 2)
        }), 201
        
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route('/api/energy/analysis', methods=['GET'])
@role_required(["Manager", "Supervisor"])
def get_energy_analysis():
    """Mendapatkan analisis konsumsi energi"""
    try:
        energy_collection = get_energy_collection()
        if energy_collection is None:
            return jsonify({"message": "Database energy collection tidak tersedia"}), 500
        
        # Get energy data from last 30 days
        thirty_days_ago = int(time.time()) - (30 * 24 * 60 * 60)
        energy_data = list(energy_collection.find({
            "timestamp": {"$gte": thirty_days_ago}
        }).sort("timestamp", 1))
        
        analysis = {
            "total_consumption": 0,
            "average_power": 0,
            "peak_consumption": 0,
            "assets_analysis": {}
        }
        
        power_values = []
        
        for record in energy_data:
            analysis["total_consumption"] += record['energy_consumption']
            power_values.append(record['power_consumption'])
            
            asset_name = record['asset_name']
            if asset_name not in analysis["assets_analysis"]:
                analysis["assets_analysis"][asset_name] = {
                    "total_energy": 0,
                    "average_power": 0,
                    "records_count": 0
                }
            
            analysis["assets_analysis"][asset_name]["total_energy"] += record['energy_consumption']
            analysis["assets_analysis"][asset_name]["records_count"] += 1
        
        if power_values:
            analysis["average_power"] = sum(power_values) / len(power_values)
            analysis["peak_consumption"] = max(power_values)
            
            # Calculate averages per asset
            for asset in analysis["assets_analysis"]:
                asset_data = analysis["assets_analysis"][asset]
                if asset_data["records_count"] > 0:
                    asset_data["average_power"] = asset_data["total_energy"] / asset_data["records_count"]
        
        return jsonify(analysis), 200
        
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

# =========================================================
# FITUR 4: Cost Analysis & Budget Tracking
# =========================================================

@app.route('/api/costs/maintenance', methods=['POST'])
@role_required(["Manager", "Supervisor"])
def record_maintenance_cost():
    """Mencatat biaya maintenance"""
    try:
        data = request.get_json()
        
        required_fields = ['wo_id', 'asset_name', 'cost_type', 'amount']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"message": f"Field {field} harus diisi"}), 400
        
        cost_data = {
            "wo_id": data['wo_id'],
            "asset_name": data['asset_name'],
            "cost_type": data['cost_type'],  # parts, labor, downtime, etc.
            "amount": data['amount'],
            "currency": data.get('currency', 'IDR'),
            "description": data.get('description', ''),
            "timestamp": int(time.time()),
            "recorded_by": session['user']['username']
        }
        
        costs_collection = get_maintenance_costs_collection()
        if costs_collection is None:
            return jsonify({"message": "Database maintenance costs collection tidak tersedia"}), 500
            
        result = costs_collection.insert_one(cost_data)
        
        return jsonify({
            "message": "Biaya maintenance berhasil dicatat",
            "cost_id": str(result.inserted_id)
        }), 201
        
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route('/api/costs/analysis', methods=['GET'])
@role_required(["Manager"])
def get_cost_analysis():
    """Mendapatkan analisis biaya maintenance"""
    try:
        costs_collection = get_maintenance_costs_collection()
        if costs_collection is None:
            return jsonify({"message": "Database maintenance costs collection tidak tersedia"}), 500
        
        # Get costs from last 12 months
        one_year_ago = int(time.time()) - (365 * 24 * 60 * 60)
        costs_data = list(costs_collection.find({
            "timestamp": {"$gte": one_year_ago}
        }))
        
        analysis = {
            "total_costs": 0,
            "costs_by_type": {},
            "costs_by_asset": {},
            "monthly_breakdown": {},
            "budget_vs_actual": {}
        }
        
        for cost in costs_data:
            amount = cost['amount']
            cost_type = cost['cost_type']
            asset_name = cost['asset_name']
            
            # Total costs
            analysis["total_costs"] += amount
            
            # Costs by type
            if cost_type not in analysis["costs_by_type"]:
                analysis["costs_by_type"][cost_type] = 0
            analysis["costs_by_type"][cost_type] += amount
            
            # Costs by asset
            if asset_name not in analysis["costs_by_asset"]:
                analysis["costs_by_asset"][asset_name] = 0
            analysis["costs_by_asset"][asset_name] += amount
            
            # Monthly breakdown
            month_key = datetime.fromtimestamp(cost['timestamp']).strftime('%Y-%m')
            if month_key not in analysis["monthly_breakdown"]:
                analysis["monthly_breakdown"][month_key] = 0
            analysis["monthly_breakdown"][month_key] += amount
        
        # Calculate ROI (simplified)
        wo_collection = get_wo_collection()
        closed_wo_count = wo_collection.count_documents({
            "status": "Ditutup",
            "timestamp_created": {"$gte": one_year_ago}
        })
        
        if analysis["total_costs"] > 0:
            analysis["cost_per_wo"] = analysis["total_costs"] / closed_wo_count
        else:
            analysis["cost_per_wo"] = 0
        
        return jsonify(analysis), 200
        
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route('/api/costs/budget', methods=['POST'])
@role_required(["Manager"])
def set_maintenance_budget():
    """Menetapkan budget maintenance"""
    try:
        data = request.get_json()
        
        required_fields = ['year', 'quarter', 'amount']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"message": f"Field {field} harus diisi"}), 400
        
        budget_data = {
            "year": data['year'],
            "quarter": data['quarter'],
            "amount": data['amount'],
            "currency": data.get('currency', 'IDR'),
            "department": data.get('department', 'Maintenance'),
            "set_by": session['user']['username'],
            "set_at": int(time.time())
        }
        
        budget_collection = get_maintenance_budget_collection()
        if budget_collection is None:
            return jsonify({"message": "Database maintenance budget collection tidak tersedia"}), 500
        
        # Check if budget already exists for this period
        existing_budget = budget_collection.find_one({
            "year": data['year'],
            "quarter": data['quarter'],
            "department": data.get('department', 'Maintenance')
        })
        
        if existing_budget:
            budget_collection.update_one(
                {"_id": existing_budget['_id']},
                {"$set": budget_data}
            )
            message = "Budget berhasil diupdate"
        else:
            budget_collection.insert_one(budget_data)
            message = "Budget berhasil ditetapkan"
        
        return jsonify({"message": message}), 200
        
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

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