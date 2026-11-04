"""
test_db.py - Prueba aislada del módulo database.py.
"""

import database as db


def main() -> None:
    print("=" * 60)
    print("PRUEBA DEL MÓDULO DE BASE DE DATOS")
    print("=" * 60)

    print("\n[1] Inicializando base de datos...")
    db.init_db()
    print("    OK")

    print("\n[2] Plazas registradas:")
    for p in db.listar_plazas():
        print(f"    [{p['id']}] {p['nombre']}")

    print("\n[3] Registrando apuestas de prueba...")
    apuestas_prueba = [
        ("Juan Pérez",     "01234567-8", 1, 42,  1),
        ("María López",    "02345678-9", 3,  7,  5),
        ("Carlos Ramírez", "03456789-0", 5, 99, 10),
    ]
    for nombre, dui, plaza_id, numero, monto in apuestas_prueba:
        r = db.registrar_apuesta(nombre, dui, plaza_id, numero, monto)
        print(f"    #{r['id']} {r['cliente_nombre']:15s} "
              f"N° {r['numero_elegido']:02d}  ${r['monto']}  "
              f"→ premio ${r['premio_potencial']}")

    print("\n[4] Apuestas activas (todas):")
    for a in db.obtener_apuestas_activas():
        print(f"    #{a['id']} [{a['plaza_nombre']:10s}] "
              f"{a['cliente_nombre']:15s} N° {a['numero_elegido']:02d}  "
              f"${a['monto']}  premio ${a['premio_potencial']}")

    print("\n[5] Apuestas activas solo de la plaza 3 (Sonsonate):")
    for a in db.obtener_apuestas_activas(plaza_id=3):
        print(f"    #{a['id']} {a['cliente_nombre']} N° {a['numero_elegido']:02d}")

    print("\n[6] Totales apostados:")
    print(f"    Total global:       ${db.total_apostado()}")
    print(f"    Total plaza 3:      ${db.total_apostado(plaza_id=3)}")

    print("\n[7] Probando validaciones (deben fallar):")
    casos_invalidos = [
        ("", "12345678-9", 1, 5, 1),
        ("Test", "", 1, 5, 1),
        ("Test", "12345678-9", 1, 150, 1),
        ("Test", "12345678-9", 1, 5, -1),
        ("Test", "12345678-9", 99, 5, 1),
        ("Test", "12345678-9", 1, 5, 2.5),   # monto decimal → rechazado
    ]
    for args in casos_invalidos:
        try:
            db.registrar_apuesta(*args)
            print(f"    FALLO: no debió aceptar {args}")
        except ValueError as e:
            print(f"    OK: rechazó → {e}")

    print("\n" + "=" * 60)
    print("PRUEBA COMPLETADA CON ÉXITO")
    print("=" * 60)


if __name__ == "__main__":
    main()