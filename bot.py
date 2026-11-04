"""
bot.py - Bot con Menú Interactivo, Vendedores, Múltiples Admins y Reportes.
"""

import logging
from datetime import time
from zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters,
)

import config
import database as db
from ticket_generator import generate_ticket_image

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- Manejador Global de Errores ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Atrapa errores para que el bot no se detenga si Telegram falla."""
    logger.error("Excepción mientras se manejaba un update:", exc_info=context.error)

# --- Estados ---
(SELECCIONANDO_PLAZA, PIDIENDO_NOMBRE, PIDIENDO_DUI, PIDIENDO_NUMERO, PIDIENDO_MONTO, ADMIN_PIDIENDO_GANADOR) = range(6)

def es_admin(update: Update) -> bool:
    return update.effective_user.id in config.ADMIN_IDS

# ---------- MENÚ PRINCIPAL ----------
async def menu_principal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    botones = [
        [InlineKeyboardButton("🎰 Nueva Apuesta", callback_data="menu_apostar")],
        [InlineKeyboardButton("📋 Ver Apuestas Activas", callback_data="menu_lista")],
    ]
    
    if es_admin(update):
        botones.append([InlineKeyboardButton("📊 Reporte de Ventas", callback_data="menu_reporte")])
        botones.append([InlineKeyboardButton("🏆 Declarar Ganador", callback_data="menu_ganador")])
        botones.append([InlineKeyboardButton("🔒 Cerrar Sorteo", callback_data="menu_cerrar")])

    markup = InlineKeyboardMarkup(botones)
    texto = "👋 ¡Bienvenido al sistema de Lotería 00-99!\nSelecciona una opción:"

    if update.callback_query:
        try:
            await update.callback_query.answer()
        except Exception:
            pass
        await update.callback_query.edit_message_text(texto, reply_markup=markup)
    else:
        await update.message.reply_text(texto, reply_markup=markup)

# ---------- FLUJO /apostar ----------
async def apostar_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if db.sorteo_esta_cerrado():
        mensaje_cierre = "🔒 El sorteo de hoy ya cerró. No se pueden registrar más apuestas.\nVuelve a intentarlo mañana."
        if update.callback_query:
            try:
                await update.callback_query.answer()
            except Exception:
                pass
            await update.callback_query.edit_message_text(mensaje_cierre)
        else:
            await update.message.reply_text(mensaje_cierre)
        return ConversationHandler.END

    context.user_data["vendedor_id"] = update.effective_user.id
    context.user_data["vendedor_nombre"] = update.effective_user.first_name
    
    plazas = db.listar_plazas()
    botones = [[InlineKeyboardButton(p["nombre"], callback_data=f"plaza:{p['id']}")] for p in plazas]
    botones.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")])

    texto = "🎰 *Nueva apuesta*\n\nPaso 1 de 5: elige la *plaza*:"
    markup = InlineKeyboardMarkup(botones)

    if update.callback_query:
        try:
            await update.callback_query.answer()
        except Exception:
            pass
        await update.callback_query.edit_message_text(texto, reply_markup=markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(texto, reply_markup=markup, parse_mode="Markdown")
    return SELECCIONANDO_PLAZA

async def seleccionar_plaza(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception:
        pass

    if query.data == "cancelar":
        await query.edit_message_text("❌ Apuesta cancelada.")
        return ConversationHandler.END

    plaza_id = int(query.data.split(":")[1])
    context.user_data["plaza_id"] = plaza_id
    plazas = {p["id"]: p["nombre"] for p in db.listar_plazas()}

    await query.edit_message_text(
        f"Plaza: *{plazas.get(plaza_id)}* ✅\n\nPaso 2 de 5: escribe el *nombre del cliente*:",
        parse_mode="Markdown",
    )
    return PIDIENDO_NOMBRE

async def recibir_nombre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = update.message.text.strip()
    if len(nombre) < 3:
        await update.message.reply_text("⚠️ El nombre debe tener al menos 3 caracteres. Intenta de nuevo:")
        return PIDIENDO_NOMBRE
    context.user_data["cliente_nombre"] = nombre
    await update.message.reply_text(f"Nombre: *{nombre}* ✅\n\nPaso 3 de 5: escribe el *DUI*:", parse_mode="Markdown")
    return PIDIENDO_DUI

async def recibir_dui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dui = update.message.text.strip().replace(" ", "")
    if len(dui) != 10 or dui[8] != "-" or not (dui[:8].isdigit() and dui[9].isdigit()):
        await update.message.reply_text("⚠️ Formato inválido. Debe ser: *01234567-8*\nIntenta de nuevo:", parse_mode="Markdown")
        return PIDIENDO_DUI
    context.user_data["cliente_dui"] = dui
    await update.message.reply_text(f"DUI: *{dui}* ✅\n\nPaso 4 de 5: escribe el *número* (00-99):", parse_mode="Markdown")
    return PIDIENDO_NUMERO

async def recibir_numero(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if not texto.isdigit() or not (0 <= int(texto) <= 99):
        await update.message.reply_text("⚠️ Número inválido. Del 00 al 99.", parse_mode="Markdown")
        return PIDIENDO_NUMERO
    context.user_data["numero_elegido"] = int(texto)
    await update.message.reply_text(f"Número: *{int(texto):02d}* ✅\n\nPaso 5 de 5: escribe el *monto* (entero):", parse_mode="Markdown")
    return PIDIENDO_MONTO

async def recibir_monto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if not texto.isdigit() or int(texto) <= 0:
        await update.message.reply_text("⚠️ Monto inválido. Entero mayor a 0.", parse_mode="Markdown")
        return PIDIENDO_MONTO

    monto = int(texto)
    try:
        apuesta = db.registrar_apuesta(
            vendedor_id=context.user_data["vendedor_id"],
            vendedor_nombre=context.user_data["vendedor_nombre"],
            cliente_nombre=context.user_data["cliente_nombre"],
            cliente_dui=context.user_data["cliente_dui"],
            plaza_id=context.user_data["plaza_id"],
            numero_elegido=context.user_data["numero_elegido"],
            monto=monto,
        )
    except ValueError as e:
        await update.message.reply_text(f"❌ Error: {e}")
        context.user_data.clear()
        return ConversationHandler.END

    plazas = {p["id"]: p["nombre"] for p in db.listar_plazas()}
    await update.message.reply_text("✅ *¡Apuesta registrada!*\nGenerando ticket...", parse_mode="Markdown")
    
    ticket_img = generate_ticket_image(
        apuesta["id"], plazas.get(apuesta["plaza_id"], "?"), apuesta["cliente_nombre"],
        apuesta["cliente_dui"], apuesta["numero_elegido"], apuesta["monto"], apuesta["premio_potencial"]
    )
    
    await update.message.reply_photo(
        photo=ticket_img, 
        caption=f"🎫 Ticket #{apuesta['id']:05d}\nVendido por: {apuesta['vendedor_nombre']}"
    )
    
    botones = [
        [InlineKeyboardButton("🎰 Nueva Apuesta", callback_data="menu_apostar")],
        [InlineKeyboardButton("📋 Ver Apuestas Activas", callback_data="menu_lista")],
    ]
    if es_admin(update):
        botones.append([InlineKeyboardButton("📊 Reporte de Ventas", callback_data="menu_reporte")])
        botones.append([InlineKeyboardButton("🏆 Declarar Ganador", callback_data="menu_ganador")])
        botones.append([InlineKeyboardButton("🔒 Cerrar Sorteo", callback_data="menu_cerrar")])
    
    await update.message.reply_text("¿Qué deseas hacer ahora?", reply_markup=InlineKeyboardMarkup(botones))
    context.user_data.clear()
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    if update.callback_query:
        try:
            await update.callback_query.answer()
        except Exception:
            pass
        await update.callback_query.edit_message_text("❌ Operación cancelada.")
    else:
        await update.message.reply_text("❌ Operación cancelada.")
    
    await menu_principal(update, context)
    return ConversationHandler.END

# ---------- COMANDOS DEL MENÚ ----------

async def lista_apuestas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query: 
        try:
            await update.callback_query.answer()
        except Exception:
            pass
    
    apuestas = db.obtener_apuestas_activas()
    if not apuestas:
        texto = "No hay apuestas activas."
    else:
        lineas = ["📋 *Apuestas activas*\n"]
        total = 0
        for a in apuestas:
            lineas.append(f"#{a['id']:05d} [{a['plaza_nombre']}] {a['cliente_nombre']} — N° *{a['numero_elegido']:02d}* — ${a['monto']}\n   👤 _Vendedor: {a['vendedor_nombre']}_")
            total += a["monto"]
        lineas.append(f"\n💰 Total: *${total}*")
        texto = "\n".join(lineas)

    markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver al Menú", callback_data="menu_volver")]])
    if update.callback_query:
        await update.callback_query.edit_message_text(texto, parse_mode="Markdown", reply_markup=markup)
    else:
        await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=markup)

async def admin_reporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not es_admin(update): return
    if update.callback_query: 
        try:
            await update.callback_query.answer()
        except Exception:
            pass
    
    reporte = db.obtener_reporte_ventas_hoy()
    
    if not reporte:
        msg = "📊 No hay ventas registradas hoy."
    else:
        # Agrupamos los datos por Plaza
        plazas_dict = {}
        total_global = 0
        
        for r in reporte:
            plaza = r['plaza_nombre']
            if plaza not in plazas_dict:
                plazas_dict[plaza] = {
                    'vendedores': [],
                    'subtotal': 0
                }
            plazas_dict[plaza]['vendedores'].append(r)
            plazas_dict[plaza]['subtotal'] += r['total_vendido']
            total_global += r['total_vendido']

        msg = "📊 *REPORTE DE VENTAS DE HOY*\n\n"
        
        # Armamos el mensaje plaza por plaza
        for plaza_nombre, datos in plazas_dict.items():
            msg += f"🏪 *{plaza_nombre}*\n"
            for v in datos['vendedores']:
                msg += f"   👤 {v['vendedor_nombre']}: {v['cantidad_tickets']} tickets → ${v['total_vendido']}\n"
            msg += f"   💵 *Subtotal: ${datos['subtotal']}*\n\n"
            
        msg += f"💰 *TOTAL GLOBAL: ${total_global}*"
    
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver al Menú", callback_data="menu_volver")]])
    
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, parse_mode="Markdown", reply_markup=markup)
    else:
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=markup)
        
async def admin_cerrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not es_admin(update): return
    if update.callback_query: 
        try:
            await update.callback_query.answer()
        except Exception:
            pass
    
    cantidad = db.cerrar_apuestas_hoy()
    msg = f"🔒 Se han cerrado {cantidad} apuestas. Las ventas están bloqueadas hasta mañana."
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver al Menú", callback_data="menu_volver")]])
    
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=markup)
    else:
        await update.message.reply_text(msg, reply_markup=markup)

async def admin_ganador_inicio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not es_admin(update): return
    if update.callback_query:
        try:
            await update.callback_query.answer()
        except Exception:
            pass
        await update.callback_query.edit_message_text("🏆 Escribe el *número ganador* (00-99):", parse_mode="Markdown")
    else:
        await update.message.reply_text("🏆 Escribe el *número ganador* (00-99):", parse_mode="Markdown")
    return ADMIN_PIDIENDO_GANADOR

async def admin_recibir_ganador(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    if not texto.isdigit() or not (0 <= int(texto) <= 99):
        await update.message.reply_text("⚠️ Número inválido. Intenta de nuevo (00-99):")
        return ADMIN_PIDIENDO_GANADOR

    num = int(texto)
    ganadores = db.obtener_ganadores_hoy(num)
    
    if not ganadores:
        msg = f"El número ganador fue *{num:02d}*. No hubo ganadores hoy."
    else:
        total_pagar = sum(g["premio_potencial"] for g in ganadores)
        msg = f"🏆 *¡TENEMOS GANADOR!* 🏆\nNúmero: *{num:02d}*\n\n"
        for g in ganadores:
            msg += f"👤 {g['cliente_nombre']} (DUI: {g['cliente_dui']})\n"
            msg += f"🏪 Plaza: {g['plaza_nombre']}\n"
            msg += f"💵 Apostó: ${g['monto']} → *Ganó: ${g['premio_potencial']}*\n"
            msg += f"🤝 _Vendido por: {g['vendedor_nombre']}_\n\n"
        msg += f"💸 Total a pagar: *${total_pagar}*"
    
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver al Menú", callback_data="menu_volver")]])
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=markup)
    return ConversationHandler.END

# ---------- TAREA 3 PM ----------
async def tarea_cierre_3pm(context: ContextTypes.DEFAULT_TYPE):
    cantidad = db.cerrar_apuestas_hoy()
    
    # Avisar a TODOS los administradores
    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"⏰ *CIERRE AUTOMÁTICO (3:00 PM)*\nSe cerraron {cantidad} apuestas.\nEntra al menú del bot para declarar al ganador o ver el reporte de ventas.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error avisando al admin {admin_id}: {e}")

# ---------- MAIN ----------
def main():
    db.init_db()
    app = Application.builder().token(config.TOKEN).build()

    conv_apuesta = ConversationHandler(
        entry_points=[
            CommandHandler("apostar", apostar_inicio),
            CallbackQueryHandler(apostar_inicio, pattern="^menu_apostar$")
        ],
        states={
            SELECCIONANDO_PLAZA: [CallbackQueryHandler(seleccionar_plaza, pattern=r"^(plaza:\d+|cancelar)$")],
            PIDIENDO_NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_nombre)],
            PIDIENDO_DUI: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_dui)],
            PIDIENDO_NUMERO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_numero)],
            PIDIENDO_MONTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_monto)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar), CallbackQueryHandler(cancelar, pattern="^cancelar$")],
        allow_reentry=True, per_message=False,
    )

    conv_admin = ConversationHandler(
        entry_points=[
            CommandHandler("ganador", admin_ganador_inicio),
            CallbackQueryHandler(admin_ganador_inicio, pattern="^menu_ganador$")
        ],
        states={
            ADMIN_PIDIENDO_GANADOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_recibir_ganador)]
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
        allow_reentry=True, per_message=False,
    )

    app.add_handler(CommandHandler("start", menu_principal))
    app.add_handler(CommandHandler("reporte", admin_reporte))
    app.add_handler(CallbackQueryHandler(menu_principal, pattern="^menu_volver$"))
    app.add_handler(CallbackQueryHandler(lista_apuestas, pattern="^menu_lista$"))
    app.add_handler(CallbackQueryHandler(admin_reporte, pattern="^menu_reporte$"))
    app.add_handler(CallbackQueryHandler(admin_cerrar, pattern="^menu_cerrar$"))
    app.add_handler(conv_apuesta)
    app.add_handler(conv_admin)

    # --- REGISTRAR EL MANEJADOR DE ERRORES GLOBAL ---
    app.add_error_handler(error_handler)

    hora_cierre = time(hour=15, minute=0, tzinfo=ZoneInfo(config.ZONA_HORARIA))
    app.job_queue.run_daily(tarea_cierre_3pm, time=hora_cierre)

    logger.info("Bot escuchando mensajes...")
    app.run_polling()

if __name__ == "__main__":
    main()