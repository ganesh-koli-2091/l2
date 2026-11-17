# SAMPLE FILE: Contains deliberate security issues for demo purposes
# This is SYNTHETIC code — not from any real system

import sqlite3
import subprocess


DB_PASSWORD = "admin123"          # hardcoded password
API_KEY = "sk-prod-abc123xyz789"  # hardcoded API key


def get_user_orders(user_id):
    conn = sqlite3.connect("orders.db")
    cursor = conn.cursor()
    # SQL injection via string concatenation
    query = "SELECT * FROM orders WHERE user_id = " + user_id
    cursor.execute(query)
    return cursor.fetchall()


def run_report(report_name):
    # Shell injection risk
    subprocess.call("generate_report.sh " + report_name, shell=True)


def hash_password(password):
    import hashlib
    # Weak hashing
    return hashlib.md5(password.encode()).hexdigest()
