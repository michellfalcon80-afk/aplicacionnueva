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
        
        # --- INSERCIÓN DE AMPLIA VARIEDAD DE PRODUCTOS ---
        cursor.execute("SELECT COUNT(*) FROM vitrina")
        if cursor.fetchone()[0] == 0:
            productos_iniciales = [
                # 🎂 Pasteles Familiares (12 porciones)
                (str(uuid.uuid4())[:8], "Pastel Familiar", "Tres Leches Clásico", 12, 4, 350.0),
                (str(uuid.uuid4())[:8], "Pastel Familiar", "Chocolate Selva Negra", 12, 3, 380.0),
                (str(uuid.uuid4())[:8], "Pastel Familiar", "Zanahoria con Crema de Queso", 12, 3, 360.0),
                (str(uuid.uuid4())[:8], "Pastel Familiar", "Red Velvet Premium", 12, 2, 390.0),
                (str(uuid.uuid4())[:8], "Pastel Familiar", "Moka y Almendras", 12, 2, 370.0),
                (str(uuid.uuid4())[:8], "Pastel Familiar", "Fresa Adecuado (Sin Azúcar)", 12, 2, 410.0),
                
                # 🥧 Tartas y Pays (8 porciones)
                (str(uuid.uuid4())[:8], "Tarta / Pay", "Frutos Rojos del Bosque", 8, 5, 240.0),
                (str(uuid.uuid4())[:8], "Tarta / Pay", "Limón con Merengue Suizo", 8, 6, 220.0),
                (str(uuid.uuid4())[:8], "Tarta / Pay", "Manzana con Canela y Crujiente", 8, 4, 230.0),
                (str(uuid.uuid4())[:8], "Tarta / Pay", "Nuez Pecana Tradicional", 8, 3, 260.0),
                (str(uuid.uuid4())[:8], "Tarta / Pay", "Queso con Zarzamora", 8, 5, 250.0),
                
                # 🧁 Cupcakes (Individuales)
                (str(uuid.uuid4())[:8], "Cupcake", "Vainilla Bourbon", 1, 24, 30.0),
                (str(uuid.uuid4())[:8], "Cupcake", "Chocolate Intenso 70%", 1, 24, 32.0),
                (str(uuid.uuid4())[:8], "Cupcake", "Red Velvet", 1, 18, 35.0),
                (str(uuid.uuid4())[:8], "Cupcake", "Limón y Semillas de Amapola", 1, 12, 32.0),
                (str(uuid.uuid4())[:8], "Cupcake", "Caramelo Salado (Salted Caramel)", 1, 18, 35.0),
                (str(uuid.uuid4())[:8], "Cupcake", "Cookies and Cream", 1, 20, 35.0),
                
                # 🍮 Flanes y Gelatinas
                (str(uuid.uuid4())[:8], "Flan / Gelatina", "Flan Napolitano Casero", 10, 4, 180.0),
                (str(uuid.uuid4())[:8], "Flan / Gelatina", "Chocoflan (Pastel Imposible)", 10, 3, 220.0),
                (str(uuid.uuid4())[:8], "Flan / Gelatina", "Gelatina Artística de Mosaico", 12, 4, 160.0),
                (str(uuid.uuid4())[:8], "Flan / Gelatina", "Gelatina de Tres Leches con Rompope", 12, 3, 190.0),
                
                # 🍰 Porciones Individuales
                (str(uuid.uuid4())[:8], "Porción Individual", "Cheesecake de Maracuyá", 1, 12, 45.0),
                (str(uuid.uuid4())[:8], "Porción Individual", "Cheesecake de Lotus Biscoff", 1, 10, 50.0),
                (str(uuid.uuid4())[:8], "Porción Individual", "Ópera Clásico Francés", 1, 8, 55.0),
                (str(uuid.uuid4())[:8], "Porción Individual", "Tiramisú al Mascarpone", 1, 12, 50.0),
                (str(uuid.uuid4())[:8], "Porción Individual", "Brownie con Nuez Fudge", 1, 15, 38.0),
                
                # 🍪 Galletas y Bocadillos (Por pieza / paquete)
                (str(uuid.uuid4())[:8], "Galletas / Bocadillos", "Chispas de Chocolate NY Style", 1, 30, 25.0),
                (str(uuid.uuid4())[:8], "Galletas / Bocadillos", "Avena, Pasas y Miel", 1, 20, 22.0),
                (str(uuid.uuid4())[:8], "Galletas / Bocadillos", "Macarons Surtidos (Caja x4)", 4, 10, 120.0),
                (str(uuid.uuid4())[:8], "Galletas / Bocadillos", "Alfajor de Maicena con Dulce de Leche", 1, 25, 28.0),
                (str(uuid.uuid4())[:8], "Galletas / Bocadillos", "Polvorón de Nuez", 1, 40, 18.0)
            ]
            cursor.executemany("INSERT INTO vitrina VALUES (?,?,?,?,?,?)", productos_iniciales)
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
            prod_sel = st.selectbox("Categoría / Producto", df_v['producto'].unique())
            sabores = df_v[df_v['producto'] == prod_sel]
            sab_sel = st.selectbox("Variedad / Sabor disponibles", sabores['sabor'])
            
            item = df_v[(df_v['producto'] == prod_sel) & (df_v['sabor'] == sab_sel)].iloc[0]
            
            # Info detallada del producto seleccionado
            st.info(f"📋 **Detalles:** {item['porciones']} porción(es) | 💰 **Precio:** ${item['precio']:.2f} | 📦 **Disponibles:** {int(item['stock'])} piezas")
            
            cant = st.number_input("Cantidad a vender", 1, int(item['stock']))
            
            if st.button("➕ Agregar al Carrito", use_container_width=True):
                st.session_state.carrito.append({
                    'id': item['id'], 'desc': f"{item['producto']} - {item['sabor']}",
                    'cant': cant, 'precio': item['precio'], 'subtotal': cant * item['precio']
                })
                st.rerun()

        with col2:
            if st.session_state.carrito:
                st.subheader("Tu Orden")
                df_car = pd.DataFrame(st.session_state.carrito)
                st.table(df_car[['desc', 'cant', 'subtotal']])
                
                total_venta = df_car['subtotal'].sum()
                st.metric(label="Total a Cobrar", value=f"${total_venta:,.2f}")
                
                if st.button("✅ Finalizar Venta", use_container_width=True):
                    for i in st.session_state.carrito:
                        run_query("UPDATE vitrina SET stock = stock - ? WHERE id = ?", (i['cant'], i['id']))
                    st.session_state.carrito = []
                    st.success("¡Venta realizada con éxito!")
                    st.rerun()

# --- 2. PEDIDOS ESPECIALES ---
elif opcion == "📅 Pedidos Especiales":
    st.header("Pedidos Personalizados")
    
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

    st.subheader("Listado de Pedidos")
    df_p = get_df("SELECT * FROM pedidos")
    
    if not df_p.empty:
        for idx, row in df_p.iterrows():
            with st.container():
                c1, c2, c3, c4 = st.columns([2, 3, 2, 2])
                c1.write(f"**{row['id']}**")
                c2.write(f"{row['cliente']} - {row['descripcion']}")
                c3.write(f"Estado: `{row['estado']}`")
                
                if row['estado'] == "PENDIENTE":
                    if c4.button("✅ Listar", key=f"done_{row['id']}"):
                        run_query("UPDATE pedidos SET estado = 'COMPLETADO' WHERE id = ?", (row['id'],))
                        st.rerun()
                
                if c4.button("🗑️ Borrar", key=f"del_{row['id']}"):
                    run_query("DELETE FROM pedidos WHERE id = ?", (row['id'],))
                    st.rerun()
                st.divider()

# --- 3. ADMIN / INVENTARIO ---
elif opcion == "⚙️ Admin / Inventario":
    st.header("Gestión de Inventario y Vitrina")
    
    with st.expander("✨ Agregar Nuevo Producto a Vitrina"):
        with st.form("add_v"):
            p = st.selectbox("Categoría", ["Pastel Familiar", "Tarta / Pay", "Cupcake", "Flan / Gelatina", "Porción Individual", "Galletas / Bocadillos"])
            s = st.text_input("Sabor / Variedad Específica")
            porc = st.number_input("Porciones que rinde", min_value=1, value=1)
            stk = st.number_input("Stock Inicial", min_value=0, value=10)
            pr = st.number_input("Precio Unitario", min_value=0.0, value=25.0)
            if st.form_submit_button("Añadir a Vitrina"):
                run_query("INSERT INTO vitrina VALUES (?,?,?,?,?,?)", (str(uuid.uuid4())[:8], p, s, porc, stk, pr))
                st.rerun()

    st.subheader("Productos en Existencia")
    df_inv = get_df("SELECT * FROM vitrina ORDER BY producto, sabor")
    
    if not df_inv.empty:
        for idx, row in df_inv.iterrows():
            col1, col2, col3, col4 = st.columns([3, 3, 2, 1])
            col1.write(f"**{row['producto']}**")
            col2.write(row['sabor'])
            
            nuevo_stock = col3.number_input("Stock", value=int(row['stock']), key=f"stk_{row['id']}", min_value=0)
            if nuevo_stock != row['stock']:
                run_query("UPDATE vitrina SET stock = ? WHERE id = ?", (nuevo_stock, row['id']))
                st.toast(f"Stock de {row['sabor']} actualizado")

            if col4.button("🗑️", key=f"del_v_{row['id']}"):
                run_query("DELETE FROM vitrina WHERE id = ?", (row['id'],))
                st.rerun()
    else:
        st.info("No hay productos registrados.")

    st.divider()
    if st.button("📥 Descargar Base de Datos"):
        if os.path.exists(DB_NAME):
            with open(DB_NAME, "rb") as f:
                st.download_button("Click aquí para descargar", f, file_name="respaldo_pasteleria.db")