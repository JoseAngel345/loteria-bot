# Bot de Lotería 00-99 🎰

Sistema automatizado de gestión de apuestas para múltiples plazas, desarrollado en Python con la librería `python-telegram-bot`. 

## Características principales
* **Registro de apuestas** por parte de múltiples vendedores.
* **Generación automática de tickets** en imagen (formato POS) con la librería Pillow.
* **Cierre automático de sorteo** a las 3:00 PM (Zona horaria de El Salvador).
* **Cálculo automático de premios** (x75 la inversión).
* **Reporte de ventas diario** agrupado por vendedor y plaza.
* **Control de acceso** para administradores (declarar ganador, cerrar sorteo, ver reportes).
* **Base de datos SQLite** local para rápida operación.

## Requisitos e Instalación
1. Clonar el repositorio.
2. Crear un entorno virtual (`python -m venv venv`).
3. Instalar dependencias (`pip install "python-telegram-bot[job-queue]" pillow`).
4. Renombrar `config.example.py` a `config.py` y agregar el Token de Telegram y los IDs de los administradores.
5. Ejecutar `python bot.py`.

## Tecnologías usadas
* Python 3
* SQLite
* python-telegram-bot
* Pillow (PIL)