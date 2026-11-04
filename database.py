"""
database.py - Módulo de base de datos con soporte para vendedores y reportes.
"""

import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "loteria.db"

PLAZAS_INICIALES = [
    (1, "Cara Sucia"), (2, "Metalio"), (3, "Sonsonate"),
    (4, "Jujutla"), (5, "Acajutla"), (6, "Juayúa"),
]

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plazas (
                id     INTEGER PRIMARY KEY,
                nombre TEXT NOT NULL UNIQUE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS apuestas (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                vendedor_id      INTEGER NOT NULL,
                vendedor_nombre  TEXT    NOT NULL,
                cliente_nombre   TEXT    NOT NULL,
                cliente_dui      TEXT    NOT NULL,
                plaza_id         INTEGER NOT NULL REFERENCES plazas(id),
                numero_elegido   INTEGER NOT NULL CHECK(numero_elegido BETWEEN 0 AND 99),
                monto            INTEGER NOT NULL CHECK(monto > 0),
                premio_potencial INTEGER NOT NULL,
                fecha_registro   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                estado           TEXT    DEFAULT 'activa'
            )
        """)
        cursor.executemany("INSERT OR IGNORE INTO plazas (id, nombre) VALUES (?, ?)", PLAZAS_INICIALES)
        conn.commit()
    finally:
        conn.close()

def listar_plazas() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT id, nombre FROM plazas ORDER BY id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def registrar_apuesta(
    vendedor_id: int, vendedor_nombre: str,
    cliente_nombre: str, cliente_dui: str,
    plaza_id: int, numero_elegido: int, monto: int
) -> dict:
    cliente_nombre = cliente_nombre.strip()
    cliente_dui = cliente_dui.strip()

    if not cliente_nombre or not cliente_dui:
        raise ValueError("Nombre y DUI son obligatorios.")
    if not (0 <= int(numero_elegido) <= 99):
        raise ValueError("El número debe estar entre 0 y 99.")
    if not isinstance(monto, int) or isinstance(monto, bool) or monto <= 0:
        raise ValueError("El monto debe ser un entero mayor a 0.")

    premio = int(monto) * 75

    conn = get_connection()
    try:
        cursor = conn.execute("""
            INSERT INTO apuestas
                (vendedor_id, vendedor_nombre, cliente_nombre, cliente_dui, plaza_id, numero_elegido, monto, premio_potencial)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (vendedor_id, vendedor_nombre, cliente_nombre, cliente_dui, plaza_id, int(numero_elegido), int(monto), premio))
        conn.commit()

        return {
            "id": cursor.lastrowid, "vendedor_nombre": vendedor_nombre,
            "cliente_nombre": cliente_nombre, "cliente_dui": cliente_dui,
            "plaza_id": plaza_id, "numero_elegido": int(numero_elegido),
            "monto": int(monto), "premio_potencial": premio,
        }
    finally:
        conn.close()

def obtener_apuestas_activas(plaza_id: Optional[int] = None) -> list[dict]:
    conn = get_connection()
    try:
        query = """
            SELECT a.*, p.nombre AS plaza_nombre FROM apuestas a
            JOIN plazas p ON p.id = a.plaza_id WHERE a.estado = 'activa'
        """
        params = []
        if plaza_id is not None:
            query += " AND a.plaza_id = ?"
            params.append(plaza_id)
        query += " ORDER BY a.id"
        
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def obtener_ganadores_hoy(numero_ganador: int) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT a.*, p.nombre AS plaza_nombre FROM apuestas a
            JOIN plazas p ON p.id = a.plaza_id
            WHERE a.numero_elegido = ? AND a.estado = 'cerrada'
              AND DATE(a.fecha_registro, 'localtime') = DATE('now', 'localtime')
        """, (numero_ganador,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def cerrar_apuestas_hoy() -> int:
    conn = get_connection()
    try:
        cursor = conn.execute("UPDATE apuestas SET estado = 'cerrada' WHERE estado = 'activa'")
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()

def sorteo_esta_cerrado() -> bool:
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT COUNT(*) as count FROM apuestas 
            WHERE estado = 'cerrada' AND DATE(fecha_registro, 'localtime') = DATE('now', 'localtime')
        """).fetchone()
        return row['count'] > 0
    finally:
        conn.close()

# --- NUEVA FUNCIÓN: REPORTE POR VENDEDOR Y PLAZA ---
def obtener_reporte_ventas_hoy() -> list[dict]:
    """Devuelve el total vendido por cada vendedor en cada plaza hoy."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT 
                a.vendedor_nombre, 
                a.plaza_id, 
                p.nombre AS plaza_nombre,
                COUNT(a.id) as cantidad_tickets,
                SUM(a.monto) as total_vendido
            FROM apuestas a
            JOIN plazas p ON p.id = a.plaza_id
            WHERE DATE(a.fecha_registro, 'localtime') = DATE('now', 'localtime')
            GROUP BY a.vendedor_nombre, a.plaza_id
            ORDER BY total_vendido DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()