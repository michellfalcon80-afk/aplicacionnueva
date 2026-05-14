import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import uuid
import streamlit.components.v1 as components
import os

# --- CONFIGURACIÓN BASE DE DATOS ---
DB_NAME = "sweet_logic_v1.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS vitrina 
                          (id TEXT PRIMARY KEY, producto TEXT, sabor TEXT, 
                           porciones INTEGER, stock INTEGER, precio REAL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS pedidos 
                          (id TEXT PRIMARY KEY, cliente TEXT, fecha_entrega TEXT, 
                           descripcion TEXT, total REAL, anticipo REAL, estado TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS ventas 
                          (id TEXT, fecha TEXT, items TEXT, total REAL)''')
        conn.commit()

def run_query(query, params=()):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()

def get_df(query, params=()):
    with sqlite3.connect(DB_NAME) as conn:
        return pd.read_sql_query(query, conn, params=params)

# --- INICIALIZACIÓN ---
st.set_page_config(page_title="SweetLogic ERP", layout="wide")
init_db()

if 'carrito' not in st.session_state: st.session_state.carrito = []

# --- MENÚ LATERAL ---
st.sidebar.title("🧁 Panel de Control")
opcion = st.sidebar.radio("Navegación", ["🛒 Venta Mostrador", "📅 Pedidos Especiales", "⚙️ Admin / Inventario"])

# --- 1. VENTA MOSTRADOR ---
if opcion == "🛒 Venta Mostrador":
    st.header("Venta de Vitrina")
    df_v = get_df("SELECT * FROM vitrina WHERE stock > 0")
    
    if df_v.empty:
        st.warning("No hay productos en vitrina. Ve a Admin para agregar.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            prod_sel = st.selectbox("Producto", df_v['producto'].unique())
            sabores = df_v[df_v['producto'] == prod_sel]
            sab_sel = st.selectbox("Sabor", sabores['sabor'])
            
            item = df_v[(df_v['producto'] == prod_sel) & (df_v['sabor'] == sab_sel)].iloc[0]
            cant = st.number_input("Cantidad", 1, int(item['stock']))
            
            if st.button("➕ Agregar al Carrito"):
                st.session_state.carrito.append({
                    'id': item['id'], 'desc': f"{item['producto']} ({item['sabor']})",
                    'cant': cant, 'precio': item['precio'], 'subtotal': cant * item['precio']
                })
                st.rerun()

        with col2:
            if st.session_state.carrito:
                st.subheader("Tu Orden")
                df_car = pd.DataFrame(st.session_state.carrito)
                st.table(df_car[['desc', 'cant', 'subtotal']])
                if st.button("✅ Finalizar Venta"):
                    for i in st.session_state.carrito:
                        run_query("UPDATE vitrina SET stock = stock - ? WHERE id = ?", (i['cant'], i['id']))
                    st.session_state.carrito = []
                    st.success("Venta realizada!")
                    st.rerun()

# --- 2. PEDIDOS ESPECIALES (CON OPCIÓN DE BORRAR/COMPLETAR) ---
elif opcion == "📅 Pedidos Especiales":
    st.header("Pedidos Personalizados")
    
    # Formulario para nuevo
    with st.expander("➕ Registrar Nuevo Pedido"):
        with st.form("nuevo_p"):
            cli = st.text_input("Cliente")
            desc = st.text_area("Descripción")
            fec = st.date_input("Entrega")
            tot = st.number_input("Total", min_value=0.0)
            if st.form_submit_button("Guardar Pedido"):
                p_id = "ORD-" + str(uuid.uuid4())[:5].upper()
                run_query("INSERT INTO pedidos VALUES (?,?,?,?,?,?,?)", 
                          (p_id, cli, str(fec), desc, tot, 0, "PENDIENTE"))
                st.rerun()

    # Listado de pedidos con acciones
    st.subheader("Listado de Pedidos")
    df_p = get_df("SELECT * FROM pedidos")
    
    if not df_p.empty:
        for idx, row in df_p.iterrows():
            with st.container():
                c1, c2, c3, c4 = st.columns([2, 3, 2, 2])
                c1.write(f"**{row['id']}**")
                c2.write(f"{row['cliente']} - {row['descripcion']}")
                c3.write(f"Estado: `{row['estado']}`")
                
                # Botones de acción
                if row['estado'] == "PENDIENTE":
                    if c4.button("✅ Listar", key=f"done_{row['id']}"):
                        run_query("UPDATE pedidos SET estado = 'COMPLETADO' WHERE id = ?", (row['id'],))
                        st.rerun()
                
                if c4.button("🗑️ Borrar", key=f"del_{row['id']}"):
                    run_query("DELETE FROM pedidos WHERE id = ?", (row['id'],))
                    st.rerun()
                st.divider()

# --- 3. ADMIN / INVENTARIO (EDICIÓN Y BORRADO) ---
elif opcion == "⚙️ Admin / Inventario":
    st.header("Gestión de Inventario y Vitrina")
    
    # Agregar nuevo
    with st.expander("✨ Agregar Nuevo Producto a Vitrina"):
        with st.form("add_v"):
            p = st.text_input("Nombre")
            s = st.text_input("Sabor")
            stk = st.number_input("Stock", min_value=0)
            pr = st.number_input("Precio", min_value=0.0)
            if st.form_submit_button("Añadir"):
                run_query("INSERT INTO vitrina VALUES (?,?,?,?,?,?)", (str(uuid.uuid4())[:8], p, s, 0, stk, pr))
                st.rerun()

    # Tabla de edición
    st.subheader("Productos en Existencia")
    df_inv = get_df("SELECT * FROM vitrina")
    
    if not df_inv.empty:
        for idx, row in df_inv.iterrows():
            col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 1])
            col1.write(row['producto'])
            col2.write(row['sabor'])
            
            # Edición rápida de stock
            nuevo_stock = col3.number_input("Stock", value=int(row['stock']), key=f"stk_{row['id']}")
            if nuevo_stock != row['stock']:
                run_query("UPDATE vitrina SET stock = ? WHERE id = ?", (nuevo_stock, row['id']))
                st.toast("Stock actualizado")

            # Botón borrar
            if col5.button("🗑️", key=f"del_v_{row['id']}"):
                run_query("DELETE FROM vitrina WHERE id = ?", (row['id'],))
                st.rerun()
    else:
        st.info("No hay productos registrados.")

    # Respaldo
    st.divider()
    if st.button("📥 Descargar Base de Datos"):
        if os.path.exists(DB_NAME):
            with open(DB_NAME, "rb") as f:
                st.download_button("Click aquí para descargar", f, file_name="respaldo_pasteleria.db")