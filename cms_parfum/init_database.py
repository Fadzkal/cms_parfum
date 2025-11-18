# init_database.py
from models import create_initial_users, create_initial_assets, create_initial_inventory, create_initial_schedule

if __name__ == '__main__':
    create_initial_users()
    create_initial_assets() 
    create_initial_inventory()
    create_initial_schedule()
    print("Database initialized successfully!")