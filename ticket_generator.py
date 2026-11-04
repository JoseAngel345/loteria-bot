"""
ticket_generator.py - Genera la imagen del ticket ajustándose a la plantilla.
"""

import io
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

TEMPLATE_PATH = Path(__file__).parent / "ticket_bg.png"

def generate_ticket_image(
    ticket_id: int,
    plaza: str,
    cliente: str,
    dui: str,
    numero: int,
    monto: int,
    premio: int
) -> io.BytesIO:
    
    # 1. Cargar la plantilla
    img = Image.open(TEMPLATE_PATH).convert("RGB")
    draw = ImageDraw.Draw(img)

    # 2. Cargar la fuente
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 28)
    except IOError:
        font = ImageFont.load_default()

    ahora = datetime.now()
    fecha_str = ahora.strftime("%d/%m/%Y")
    hora_str = ahora.strftime("%I:%M %p")

    # ==========================================
    # CONFIGURACIÓN DE COORDENADAS (X, Y)
    # Cambia estos valores para mover cada texto.
    # X: Distancia desde la izquierda.
    # Y: Distancia desde arriba.
    # ==========================================
    
    x_numero = 270  
    y_numero = 375
    
    x_monto  = 270 
    y_monto  = 410
    
    x_premio = 270  
    y_premio = 448
    
    x_fecha  = 180  
    y_fecha  = 489
    
    x_hora   = 180
    y_hora   = 530
    
    x_dui    = 180 
    y_dui    = 570

    # 4. Escribir los datos (Ahora cada uno usa su propia X y Y)
    draw.text((x_numero, y_numero), f"{numero:02d}", font=font, fill="black")
    draw.text((x_monto, y_monto), f"${monto}", font=font, fill="black")
    draw.text((x_premio, y_premio), f"${premio}", font=font, fill="black")
    draw.text((x_fecha, y_fecha), f"{fecha_str}", font=font, fill="black")
    draw.text((x_hora, y_hora), f"{hora_str}", font=font, fill="black")
    draw.text((x_dui, y_dui), f"{dui}", font=font, fill="black")

    # 5. Guardar en memoria
    output = io.BytesIO()
    img.save(output, format="PNG")
    output.seek(0)
    
    return output