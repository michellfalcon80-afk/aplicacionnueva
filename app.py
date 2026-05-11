import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import uuid
import streamlit.components.v1 as components

# --- DATABASE SETUP ---
DB_NAME = "nexus_projects.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # Tabla de Proyectos
        cursor.execute('''CREATE TABLE IF NOT EXISTS proyectos 
                          (id TEXT PRIMARY KEY, nombre TEXT, responsable TEXT, prioridad TEXT, limite TEXT)''')
        # Tabla de Tareas (Relacionada)
        cursor.execute('''CREATE TABLE IF NOT EXISTS tareas 
                          (id TEXT PRIMARY KEY, proyecto_id TEXT, descripcion TEXT, estado TEXT, horas_est REAL)''')
        conn.commit()

def run_query(query, params=()):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()

def get_df(query, params=()):
    with sqlite3.connect(DB_NAME) as conn:
        return pd.read_sql_query(query, conn, params=params)

# --- SISTEMA DE NOTIFICACIÓN VISUAL (JS) ---
def lanzar_alerta(mensaje):
    components.html(f"""
    <script>
        alert("{mensaje}");
    </script>
    """, height=0)

# --- UI CONFIG ---
st.set_page_config(page_title="Nexus PM", layout="wide", page_icon="🚀")
init_db()

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("NEXUS PROJECT MANAGER")
menu = ["📊 Dashboard", "🆕 Nuevo Proyecto", "📋 Tablero de Tareas", "🧹 Gestión de Datos"]
choice = st.sidebar.selectbox("Ir a:", menu)

# --- 1. DASHBOARD (Visualización de Complejidad) ---
if choice == "📊 Dashboard":
    st.header("Estado Global de Proyectos")
    df_p = get_df("SELECT * FROM proyectos")
    
    if not df_p.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Proyectos Totales", len(df_p))
        
        df_t = get_df("SELECT * FROM tareas")
        col2.metric("Tareas Pendientes", len(df_t[df_t['estado'] != 'Completada']))
        col3.metric("Horas Totales Estimadas", f"{df_t['horas_est'].sum()} hrs")

        st.subheader("Cronograma de Entrega")
        # Mostramos los proyectos ordenados por fecha límite
        st.dataframe(df_p.sort_values(by="limite"), use_container_width=True)
    else:
        st.info("No hay proyectos registrados aún.")

# --- 2. NUEVO PROYECTO ---
elif choice == "🆕 Nuevo Proyecto":
    st.header("Crear Nuevo Proyecto")
    with st.form("form_proyecto"):
        nombre = st.text_input("Nombre del Proyecto")
        resp = st.text_input("Líder de Proyecto")
        prioridad = st.select_slider("Nivel de Prioridad", options=["Baja", "Media", "Alta", "Crítica"])
        fecha_limite = st.date_input("Fecha de Entrega")
        
        if st.form_submit_button("Inicializar Proyecto"):
            if nombre and resp:
                p_id = str(uuid.uuid4())[:8].upper()
                run_query("INSERT INTO proyectos VALUES (?,?,?,?,?)", 
                          (p_id, nombre, resp, prioridad, str(fecha_limite)))
                st.success(f"Proyecto {p_id} creado con éxito.")
                lanzar_alerta(f"Proyecto {nombre} ha sido guardado.")
            else:
                st.error("Por favor llena todos los campos.")

# --- 3. TABLERO DE TAREAS (Lógica de Relación) ---
elif choice == "📋 Tablero de Tareas":
    st.header("Gestión de Tareas")
    df_p = get_df("SELECT id, nombre FROM proyectos")
    
    if not df_p.empty:
        # Seleccionar Proyecto
        dict_proyectos = dict(zip(df_p['nombre'], df_p['id']))
        p_sel_nombre = st.selectbox("Selecciona un Proyecto para gestionar", df_p['nombre'])
        p_id_actual = dict_proyectos[p_sel_nombre]

        # Agregar Tarea
        with st.expander("➕ Añadir Tarea al Proyecto"):
            c1, c2, c3 = st.columns([3, 1, 1])
            desc = c1.text_input("Descripción de la tarea")
            horas = c2.number_input("Horas Est.", 0.5, 100.0, 1.0)
            if c3.button("Añadir", use_container_width=True):
                t_id = "TASK-" + str(uuid.uuid4())[:4].upper()
                run_query("INSERT INTO tareas VALUES (?,?,?,?,?)", 
                          (t_id, p_id_actual, desc, "Pendiente", horas))
                st.rerun()

        # Mostrar y Editar Tareas
        st.divider()
        df_t = get_df("SELECT id, descripcion, estado, horas_est FROM tareas WHERE proyecto_id = ?", (p_id_actual,))
        
        if not df_t.empty:
            for index, row in df_t.iterrows():
                col_t1, col_t2, col_t3 = st.columns([4, 2, 1])
                col_t1.write(f"**{row['descripcion']}** ({row['id']})")
                
                # Cambio de estado dinámico
                nuevo_estado = col_t2.selectbox("Estado", ["Pendiente", "En Proceso", "Completada"], 
                                               index=["Pendiente", "En Proceso", "Completada"].index(row['estado']),
                                               key=f"sel_{row['id']}")
                
                if nuevo_estado != row['estado']:
                    run_query("UPDATE tareas SET estado = ? WHERE id = ?", (nuevo_estado, row['id']))
                    st.rerun()
                
                if col_t3.button("🗑️", key=f"del_{row['id']}"):
                    run_query("DELETE FROM tareas WHERE id = ?", (row['id'],))
                    st.rerun()
        else:
            st.info("Este proyecto aún no tiene tareas.")
    else:
        st.warning("Primero debes crear un proyecto en la sección correspondiente.")

# --- 4. GESTIÓN DE DATOS ---
elif choice == "🧹 Gestión de Datos":
    st.header("Herramientas de Administrador")
    
    tab1, tab2 = st.tabs(["Exportar", "Reset"])
    
    with tab1:
        st.subheader("Exportar a CSV")
        if st.button("Generar Reporte Consolidado"):
            full_data = get_df('''SELECT p.nombre, p.responsable, t.descripcion, t.estado, t.horas_est 
                                  FROM proyectos p LEFT JOIN tareas t ON p.id = t.proyecto_id''')
            st.dataframe(full_data)
            csv = full_data.to_csv(index=False).encode('utf-8')
            st.download_button("Descargar CSV", csv, "reporte_nexus.csv", "text/csv")

    with tab2:
        st.subheader("Zona de Peligro")
        if st.button("⚠️ Borrar TODA la base de datos"):
            run_query("DELETE FROM tareas")
            run_query("DELETE FROM proyectos")
            st.error("Datos eliminados permanentemente.")
            st.rerun()