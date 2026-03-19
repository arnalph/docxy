import sqlite3
import hashlib

def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()

def check_db():
    conn = sqlite3.connect('docxy.db')
    cursor = conn.cursor()
    
    print("Tables:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    print(cursor.fetchall())
    
    print("\nUsers:")
    cursor.execute("SELECT id, email FROM users;")
    users = cursor.fetchall()
    print(users)
    
    print("\nAPI Keys:")
    cursor.execute("SELECT id, user_id, key_prefix FROM api_keys;")
    print(cursor.fetchall())
    
    conn.close()

if __name__ == "__main__":
    check_db()
