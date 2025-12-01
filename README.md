CMS Parfum - Maintenance Management System
Sistem Manajemen Perawatan (Maintenance Management System) untuk industri parfum yang dibangun dengan Flask dan MongoDB.

📋 Fitur Utama
🎯 Role-Based Access Control (RBAC)
Manager: Analisis KPI, pengaturan budget, monitoring performa

Supervisor: Verifikasi WO, alokasi teknisi, monitoring jadwal

Teknisi: Eksekusi WO, pelaporan, upload foto

Operator: Permintaan WO, monitoring aset, notifikasi jadwal

🔧 Core Functionality
Work Order Management - Siklus lengkap dari permintaan hingga penutupan

Asset Tracking - Monitoring performa dan status mesin

Inventory Management - Manajemen sparepart dengan notifikasi low stock

Maintenance Scheduling - Jadwal preventive dan predictive maintenance

Photo Documentation - Upload foto untuk dokumentasi WO

📊 Advanced Features
OEE Calculation - Overall Equipment Effectiveness untuk analisis performa

Predictive Maintenance - Prediksi kerusakan berdasarkan data sensor

Energy Monitoring - Analisis konsumsi energi per mesin

Cost Analysis - Pelacakan biaya maintenance dan budget tracking

KPI Analytics - MTTR, availability, compliance rate, dll.

🛠️ Teknologi
Backend: Python Flask

Database: MongoDB

Authentication: Session-based dengan role management

File Upload: Support gambar (PNG, JPG, JPEG, GIF)

CORS: Cross-Origin Resource Sharing enabled

🚀 Instalasi
Prerequisites
Python 3.8+

MongoDB 4.4+

pip package manager

Langkah Instalasi
Clone Repository

bash
git clone https://github.com/username/cms_parfum.git
cd cms_parfum
Buat Virtual Environment

bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
Install Dependencies

bash
pip install -r requirements.txt
Konfigurasi Database

bash
# Pastikan MongoDB berjalan
mongod --dbpath /path/to/data/db
Inisialisasi Database

bash
python init_database.py
Jalankan Aplikasi

bash
python app.py
Aplikasi akan berjalan di http://localhost:5000

👥 User Login Default
Role	Username	Password	Dashboard
Operator	op_lina	123	/dashboard/operator
Teknisi	tech_budi	123	/dashboard/teknisi
Supervisor	sup_adi	123	/dashboard/supervisor
Manager	mgr_maya	123	/dashboard/manager
📁 Struktur File
text
cms_parfum/
├── app.py                 # Main Flask application
├── models.py              # Database models & initial data
├── db_config.py           # MongoDB configuration
├── init_database.py       # Database initialization script
├── requirements.txt       # Python dependencies
├── static/               # Static files
│   └── uploads/          # Uploaded photos
├── templates/            # HTML templates
│   ├── dashboard_manager.html
│   ├── dashboard_operator.html
│   ├── dashboard_supervisor.html
│   ├── dashboard_teknisi.html
│   ├── landing.html
│   └── login.html
└── README.md             # This file
🔌 API Endpoints
Authentication
GET / - Landing page

GET/POST /login - User login

GET /logout - User logout

GET /api/user-info - Get current user info

Work Orders
Operator: POST /api/wo/request - Buat permintaan WO

Teknisi: POST /api/wo/complete/<id> - Selesaikan WO

Supervisor: POST /api/wo/verify/<id> - Verifikasi WO

All: GET /api/wo - Lihat WO berdasarkan status

All: GET /api/work_orders/history - Riwayat WO lengkap

Assets Management
GET /api/assets - Daftar aset

GET /api/assets/detail - Detail aset

POST /api/assets/create - Tambah aset baru

GET /api/assets/<name>/components - Komponen aset

Inventory
GET /api/inventory - Daftar inventory

GET /api/inventory/low-stock - Item stock rendah

POST /api/inventory/update/<id> - Update stock

Maintenance Schedule
GET /api/schedule - Semua jadwal

GET /api/schedule/upcoming - Jadwal mendatang

POST /api/schedule/create - Buat jadwal baru

GET /api/schedule/technician - Jadwal untuk teknisi

GET /api/schedule/operator - Jadwal untuk operator

KPI & Analytics
GET /api/kpi/mttr - Hitung MTTR

GET /api/kpi/assets - KPI aset

GET /api/kpi/dashboard - Dashboard KPI

Advanced Features
POST /api/oee/calculate - Hitung OEE

POST /api/predictive/maintenance - Predictive maintenance

POST /api/energy/consumption - Record energy consumption

POST /api/costs/maintenance - Record maintenance costs

POST /api/costs/budget - Set maintenance budget

User Management (Manager/Supervisor)
POST /api/admin/register - Register user baru

GET /api/admin/users - Daftar semua users

📊 Database Collections
users - Data pengguna

assets - Data mesin dan aset

work_orders - Data work orders

inventory - Data sparepart

maintenance_schedule - Jadwal maintenance

energy_consumption - Data konsumsi energi

maintenance_costs - Data biaya maintenance

maintenance_budget - Data budget maintenance

predictive_maintenance - Data predictive maintenance

🔐 Role Permissions
Permission	Operator	Teknisi	Supervisor	Manager
Create WO	✅	❌	❌	❌
View Assigned WO	❌	✅	✅	✅
Start/Complete WO	❌	✅	❌	❌
Verify/Close WO	❌	❌	✅	✅
Assign WO	❌	❌	✅	✅
View All Assets	✅	✅	✅	✅
Create Assets	❌	❌	✅	✅
View Inventory	❌	✅	✅	✅
Update Inventory	❌	❌	✅	❌
View KPI	❌	❌	✅	✅
Register Users	❌	❌	✅	✅
Budget Management	❌	❌	❌	✅
🖼️ Photo Upload
Format: PNG, JPG, JPEG, GIF

Max size: 16MB

Upload saat: Pembuatan WO, penyelesaian WO, verifikasi

Storage: static/uploads/

🎯 KPI yang Tersedia
MTTR (Mean Time To Repair) - Rata-rata waktu perbaikan

OEE (Overall Equipment Effectiveness) - Efektivitas peralatan

Asset Availability - Ketersediaan aset

PM Compliance - Compliance preventive maintenance

Cost Per WO - Biaya rata-rata per work order

Energy Efficiency - Efisiensi energi per mesin

🔧 Database Initialization
Database diinisialisasi dengan data realistis untuk:

4 user dengan role berbeda

6 mesin dengan spesifikasi lengkap

Inventory sparepart untuk semua komponen mesin

Data energi dan biaya untuk analisis

Data predictive maintenance untuk simulasi

🚀 Deployment
Lokal Development
bash
python app.py
Production (Contoh dengan Gunicorn)
bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
Environment Variables
bash
export MONGO_URI="mongodb://localhost:27017/"
export SECRET_KEY="your-secret-key-here"
📝 Catatan Penting
MongoDB default berjalan di port 27017

Secret key default hanya untuk development

Upload folder dibuat otomatis saat pertama run

Database direset dengan init_database.py

Foto disimpan dengan nama unik untuk keamanan

🐛 Troubleshooting
Port 5000 sudah digunakan:

bash
python app.py --port 5001
MongoDB connection error:

Pastikan MongoDB service berjalan

Cek konfigurasi di db_config.py

Photo upload gagal:

Cek folder static/uploads/ permissions

Pastikan file < 16MB

Format file harus PNG/JPG/JPEG/GIF

📄 License
Proprietary - Hak cipta milik Prime Fragrance Technologies 2024

👥 Kontribusi
Fork repository

Buat branch fitur (git checkout -b feature/AmazingFeature)

Commit perubahan (git commit -m 'Add some AmazingFeature')

Push ke branch (git push origin feature/AmazingFeature)

Buat Pull Request

📞 Support
Untuk bantuan atau pertanyaan:

Buka issue di GitHub

Hubungi tim development
