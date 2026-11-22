from pathlib import Path
import sqlite3

ROOT=Path(__file__).resolve().parents[1]
DB_PATH=ROOT/"inventory.db"

def connect():
    conn=sqlite3.connect(DB_PATH,check_same_thread=False)
    conn.row_factory=sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS materials(
          material_id INTEGER PRIMARY KEY AUTOINCREMENT, sku TEXT UNIQUE NOT NULL,
          material_name TEXT NOT NULL, category TEXT NOT NULL, unit TEXT NOT NULL DEFAULT 'pcs',
          current_stock REAL NOT NULL DEFAULT 0 CHECK(current_stock>=0),
          minimum_stock REAL NOT NULL DEFAULT 0 CHECK(minimum_stock>=0),
          lead_time_days INTEGER NOT NULL DEFAULT 3 CHECK(lead_time_days>0), supplier TEXT DEFAULT '',
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS transactions(
          transaction_id INTEGER PRIMARY KEY AUTOINCREMENT, material_id INTEGER NOT NULL,
          transaction_type TEXT NOT NULL CHECK(transaction_type IN ('STOCK_IN','STOCK_OUT','STOCK_OPNAME')),
          quantity REAL NOT NULL CHECK(quantity>0), note TEXT DEFAULT '', transaction_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY(material_id) REFERENCES materials(material_id) ON DELETE RESTRICT);
        CREATE INDEX IF NOT EXISTS idx_transactions_material_date ON transactions(material_id,transaction_date);
        """)

def seed_if_empty():
    seed=[
      ("PKG001","Kardus Hampers Small","Packaging","pcs",42,30,5,"CV Mitra Kemasan"),
      ("PKG002","Kardus Hampers Large","Packaging","pcs",18,25,7,"CV Mitra Kemasan"),
      ("PKG003","Pita Satin Gold","Packaging","roll",12,8,4,"Toko Pita Jaya"),
      ("PKG004","Bubble Wrap","Packaging","roll",7,10,3,"CV Aman Pack"),
      ("PKG005","Kertas Tissue","Packaging","pack",35,15,3,"CV Aman Pack"),
      ("MAT001","Handuk Polos","Bahan Baku","pcs",65,40,10,"Supplier Tekstil A"),
      ("MAT002","Sajadah Polos","Bahan Baku","pcs",24,30,12,"Supplier Tekstil B"),
      ("MAT003","Kartu Ucapan","Pelengkap","pcs",90,50,4,"Percetakan Kita"),
      ("MAT004","Plastik OPP","Packaging","pack",9,12,5,"CV Aman Pack"),
      ("MAT005","Stiker Logo Firaza","Pelengkap","sheet",22,10,6,"Percetakan Kita")]
    with connect() as c:
        if c.execute("SELECT COUNT(*) FROM materials").fetchone()[0]==0:
            c.executemany("INSERT INTO materials(sku,material_name,category,unit,current_stock,minimum_stock,lead_time_days,supplier) VALUES(?,?,?,?,?,?,?,?)",seed)
            # Explicitly synthetic demo history to make usage features calculable.
            for mid in range(1,len(seed)+1):
                c.execute("INSERT INTO transactions(material_id,transaction_type,quantity,note,transaction_date) VALUES(?,?,?,?,datetime('now','-10 days'))",(mid,"STOCK_OUT",[8,12,3,6,10,15,9,20,5,4][mid-1],"Synthetic demo usage"))
                c.execute("INSERT INTO transactions(material_id,transaction_type,quantity,note,transaction_date) VALUES(?,?,?,?,datetime('now','-3 days'))",(mid,"STOCK_OUT",[4,8,2,4,5,7,6,8,3,2][mid-1],"Synthetic demo usage"))

def get_materials():
    with connect() as c: return c.execute("SELECT * FROM materials ORDER BY material_name").fetchall()

def add_material(sku,name,category,unit,stock,minimum,lead_time,supplier):
    with connect() as c: c.execute("INSERT INTO materials(sku,material_name,category,unit,current_stock,minimum_stock,lead_time_days,supplier) VALUES(?,?,?,?,?,?,?,?)",(sku,name,category,unit,stock,minimum,lead_time,supplier))

def update_material(material_id,name,category,unit,minimum,lead_time,supplier):
    with connect() as c:
        cur=c.execute("UPDATE materials SET material_name=?,category=?,unit=?,minimum_stock=?,lead_time_days=?,supplier=?,updated_at=CURRENT_TIMESTAMP WHERE material_id=?",(name,category,unit,minimum,lead_time,supplier,material_id))
        if cur.rowcount==0: raise ValueError("Material tidak ditemukan.")

def delete_material(material_id):
    with connect() as c:
        if c.execute("SELECT COUNT(*) FROM transactions WHERE material_id=?",(material_id,)).fetchone()[0]: raise ValueError("Material memiliki riwayat transaksi dan tidak dapat dihapus. Ubah status secara manual atau pertahankan histori.")
        c.execute("DELETE FROM materials WHERE material_id=?",(material_id,))

def record_transaction(material_id,tx_type,quantity,note=""):
    if quantity<=0: raise ValueError("Quantity harus lebih besar dari 0.")
    if tx_type not in ("STOCK_IN","STOCK_OUT","STOCK_OPNAME"): raise ValueError("Jenis transaksi tidak valid.")
    with connect() as c:
        m=c.execute("SELECT current_stock FROM materials WHERE material_id=?",(material_id,)).fetchone()
        if m is None: raise ValueError("Material tidak ditemukan.")
        current=float(m['current_stock'])
        new=current+quantity if tx_type=="STOCK_IN" else current-quantity if tx_type=="STOCK_OUT" else quantity
        if new<0: raise ValueError("Stock-out melebihi stok tersedia.")
        c.execute("INSERT INTO transactions(material_id,transaction_type,quantity,note) VALUES(?,?,?,?)",(material_id,tx_type,quantity,note))
        c.execute("UPDATE materials SET current_stock=?,updated_at=CURRENT_TIMESTAMP WHERE material_id=?",(new,material_id))

def get_transactions(limit=500):
    with connect() as c: return c.execute("SELECT t.transaction_id,m.sku,m.material_name,t.transaction_type,t.quantity,m.unit,t.note,t.transaction_date FROM transactions t JOIN materials m ON t.material_id=m.material_id ORDER BY t.transaction_date DESC,t.transaction_id DESC LIMIT ?",(limit,)).fetchall()

def get_usage_features():
    with connect() as c:
        rows=c.execute("""SELECT m.material_id,
          COALESCE(SUM(CASE WHEN t.transaction_type='STOCK_OUT' AND t.transaction_date>=datetime('now','-7 days') THEN t.quantity ELSE 0 END),0) usage_7d,
          COALESCE(SUM(CASE WHEN t.transaction_type='STOCK_OUT' AND t.transaction_date>=datetime('now','-30 days') THEN t.quantity ELSE 0 END),0) usage_30d
          FROM materials m LEFT JOIN transactions t ON m.material_id=t.material_id GROUP BY m.material_id""").fetchall()
    return {r['material_id']:{'usage_7d':float(r['usage_7d']),'usage_30d':float(r['usage_30d'])} for r in rows}
