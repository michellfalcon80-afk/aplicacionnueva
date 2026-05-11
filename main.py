import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import uuid

# --- CAPA DE DATOS ---
DB_NAME = "novasync_erp.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # Clientes
        c.execute('''CREATE TABLE IF NOT EXISTS clientes 
                     (id TEXT PRIMARY KEY, nombre TEXT, telefono TEXT, email TEXT)''')
        # Servicios
        c.execute('''CREATE TABLE IF NOT EXISTS servicios 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, precio REAL, duracion INTEGER)''')
        # Citas (Relacional)
        c.execute('''CREATE TABLE IF NOT EXISTS citas 
                     (id TEXT PRIMARY KEY, cliente_id TEXT, servicio_id INTEGER, 
                      fecha TEXT, hora TEXT, estado TEXT, total REAL)''')
        conn.commit()

def query(sql, params=(), is_select=True):
    with sqlite3.connect(DB_NAME) as conn:
        if is_select:
            return pd.read_sql_query(sql, conn, params=params)
        else:
            conn.execute(sql, params)
            conn.commit()

# --- VISTAS DEL SISTEMA ---

def view_dashboard():
    st.header("📊 Tablero de Control")
    col1, col2, col3 = st.columns(3)
    
    # KPIs Reales de la BD
    total_ingresos = query("SELECT SUM(total) as t FROM citas WHERE estado='Completada'").iloc[0]['t'] or 0
    citas_hoy = len(query("SELECT id FROM citas WHERE fecha = ?", (date.today().isoformat(),)))
    clientes_total = len(query("SELECT id FROM clientes"))
    
    col1.metric("Ingresos Totales", f"${total_ingresos:,.2f}")
    col2.metric("Citas para Hoy", citas_hoy)
    col3.metric("Clientes Registrados", clientes_total)
    
    st.subheader("Próximas Citas")
    df_citas = query('''SELECT c.hora, cl.nombre as cliente, s.nombre as servicio, c.estado 
                        FROM citas c 
                        JOIN clientes cl ON c.cliente_id = cl.id 
                        JOIN servicios s ON c.servicio_id = s.id
                        WHERE c.fecha >= ? ORDER BY c.fecha ASC LIMIT 5''', (date.today().isoformat(),))
    st.table(df_citas)

def view_clientes():
    st.header("👥 Gestión de Clientes")
    with st.expander("➕ Registrar Nuevo Cliente"):
        with st.form("form_cliente"):
            nom = st.text_input("Nombre Completo")
            tel = st.text_input("Teléfono")
            mail = st.text_input("Email")
            if st.form_submit_button("Guardar"):
                c_id = str(uuid.uuid4())[:8].upper()
                query("INSERT INTO clientes VALUES (?,?,?,?)", (c_id, nom, tel, mail), False)
                st.success("Cliente registrado.")
                st.rerun()
    
    st.dataframe(query("SELECT * FROM clientes"), use_container_width=True)

def view_reservas():
    st.header("📅 Agenda de Citas")
    
    # Cargar datos para los selects
    df_cl = query("SELECT id, nombre FROM clientes")
    df_sv = query("SELECT id, nombre, precio FROM servicios")
    
    if df_cl.empty or df_sv.empty:
        st.warning("Necesitas registrar clientes y servicios antes de crear citas.")
        return

    with st.expander("🆕 Agendar Nueva Cita"):
        with st.form("form_cita"):
            cli = st.selectbox("Cliente", df_cl['nombre'])
            ser = st.selectbox("Servicio", df_sv['nombre'])
            fec = st.date_input("Fecha", min_value=date.today())
            hor = st.time_input("Hora")
            
            if st.form_submit_button("Confirmar Reserva"):
                id_c = df_cl[df_cl['nombre'] == cli]['id'].values[0]
                id_s = df_sv[df_sv['nombre'] == ser]['id'].values[0]
                precio = df_sv[df_sv['nombre'] == ser]['precio'].values[0]
                cita_id = "RES-" + str(uuid.uuid4())[:6].upper()
                
                query("INSERT INTO citas VALUES (?,?,?,?,?,?,?)", 
                      (cita_id, id_c, int(id_s), fec.isoformat(), hor.strftime("%H:%M"), "Pendiente", precio), False)
                st.success("Cita agendada correctamente.")
                st.rerun()

    # Filtros de visualización
    estado_f = st.multiselect("Filtrar por estado:", ["Pendiente", "Completada", "Cancelada"], default=["Pendiente"])
    df_res = query(f'''SELECT c.id, cl.nombre as cliente, s.nombre as servicio, c.fecha, c.hora, c.estado, c.total 
                       FROM citas c JOIN clientes cl ON c.cliente_id = cl.id 
                       JOIN servicios s ON c.servicio_id = s.id 
                       WHERE c.estado IN ({','.join(['?']*len(estado_f))})''', tuple(estado_f))
    
    st.dataframe(df_res, use_container_width=True)
    
    # Gestión de estados
    st.subheader("Actualizar Estado")
    c_sel = st.selectbox("Seleccione ID de cita", df_res['id'] if not df_res.empty else ["N/A"])
    n_est = st.radio("Nuevo Estado", ["Completada", "Cancelada"], horizontal=True)
    if st.button("Actualizar") and c_sel != "N/A":
        query("UPDATE citas SET estado = ? WHERE id = ?", (n_est, c_sel), False)
        st.rerun()

def view_config():
    st.header("⚙️ Configuración de Servicios")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Añadir Servicio")
        with st.form("sv"):
            n = st.text_input("Nombre")
            p = st.number_input("Precio", min_value=0.0)
            d = st.number_input("Duración (min)", min_value=15, step=15)
            if st.form_submit_button("Crear"):
                query("INSERT INTO servicios (nombre, precio, duracion) VALUES (?,?,?)", (n, p, d), False)
                st.rerun()
    
    with col2:
        st.subheader("Servicios Activos")
        st.write(query("SELECT * FROM servicios"))

# --- MAIN ---

def main():
    st.set_page_config(page_title="NovaSync ERP", layout="wide")
    init_db()
    
    st.sidebar.title("🚀 NovaSync ERP")
    st.sidebar.markdown("Gestión Empresarial v2.0")
    
    menu = {
        "Dashboard": {"icon": "📊", "func": view_dashboard},
        "Clientes": {"icon": "👥", "func": view_clientes},
        "Reservas": {"icon": "📅", "func": view_reservas},
        "Servicios": {"icon": "⚙️", "func": view_config}
    }
    
    choice = st.sidebar.radio("Módulos", list(menu.keys()))
    
    # Ejecutar la función correspondiente
    menu[choice]["func"]()

if __name__ == "__main__":
    main()