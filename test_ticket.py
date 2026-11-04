from ticket_generator import generate_ticket_image

def main():
    print("Generando ticket de prueba...")
    
    # Datos ficticios
    img_buffer = generate_ticket_image(
        ticket_id=1,
        plaza="Sonsonate",
        cliente="Juan Pérez",
        dui="01234567-8",
        numero=42,
        monto=5,
        premio=375
    )

    # Guardar en disco para verlo
    with open("ticket_prueba.png", "wb") as f:
        f.write(img_buffer.getvalue())
        
    print("✅ Ticket generado como 'ticket_prueba.png'")
    print("Ábrelo en tu visor de imágenes para verificar las posiciones.")

if __name__ == "__main__":
    main()