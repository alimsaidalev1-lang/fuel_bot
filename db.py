# db.py
import sqlite3
from typing import List, Tuple, Optional

def get_conn(path: str = "data.db"):
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(path: str = "data.db"):
    conn = get_conn(path)
    cur = conn.cursor()
    # таблица остатков: fuel хранит текущий остаток
    cur.execute("""
    CREATE TABLE IF NOT EXISTS stocks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fuel TEXT UNIQUE COLLATE NOCASE,
        amount REAL DEFAULT 0
    )
    """)
    # таблица выдач (history)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        fuel TEXT,
        amount REAL,
        callsign TEXT,
        source TEXT, -- ИШР или ИСР или другой
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    return conn

# stocks functions
def set_stock(conn: sqlite3.Connection, fuel: str, amount: float):
    cur = conn.cursor()
    cur.execute("INSERT INTO stocks(fuel, amount) VALUES (?, ?) ON CONFLICT(fuel) DO UPDATE SET amount=excluded.amount", (fuel, amount))
    conn.commit()

def add_stock(conn: sqlite3.Connection, fuel: str, delta: float):
    cur = conn.cursor()
    cur.execute("SELECT amount FROM stocks WHERE fuel = ?", (fuel,))
    row = cur.fetchone()
    if row:
        new = row["amount"] + delta
        cur.execute("UPDATE stocks SET amount = ? WHERE fuel = ?", (new, fuel))
    else:
        cur.execute("INSERT INTO stocks(fuel, amount) VALUES (?, ?)", (fuel, delta))
    conn.commit()

def get_stocks(conn: sqlite3.Connection) -> List[Tuple[str, float]]:
    cur = conn.cursor()
    cur.execute("SELECT fuel, amount FROM stocks")
    return [(r["fuel"], r["amount"]) for r in cur.fetchall()]

def get_stock(conn: sqlite3.Connection, fuel: str) -> Optional[float]:
    cur = conn.cursor()
    cur.execute("SELECT amount FROM stocks WHERE fuel = ?", (fuel,))
    r = cur.fetchone()
    return r["amount"] if r else None

# issues functions
def add_issue(conn: sqlite3.Connection, date: str, fuel: str, amount: float, callsign: str, source: str):
    cur = conn.cursor()
    cur.execute("INSERT INTO issues(date, fuel, amount, callsign, source) VALUES (?, ?, ?, ?, ?)", (date, fuel, amount, callsign, source))
    conn.commit()

def get_issues_by_source(conn: sqlite3.Connection, source: str):
    cur = conn.cursor()
    cur.execute("SELECT date, fuel, amount, callsign, source FROM issues WHERE source = ? ORDER BY id DESC", (source,))
    return cur.fetchall()

def get_all_issues(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("SELECT date, fuel, amount, callsign, source FROM issues ORDER BY id DESC")
    return cur.fetchall()
