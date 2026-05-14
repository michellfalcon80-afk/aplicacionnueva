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
        # Inventario de productos listos (Vitrina)
        cursor.execute('''CREATE TABLE IF NOT EXISTS vitrina 
                          (id TEXT PRIMARY KEY, producto TEXT, sabor TEXT, 
                           porciones INTEGER, stock INTEGER, precio REAL)''')
        # Pedidos personalizados (A pedido)
        cursor.execute('''CREATE TABLE IF NOT EXISTS pedidos 
                          (id TEXT PRIMARY KEY, cliente TEXT, fecha_entrega TEXT, 
                           descripcion TEXT, total REAL, anticipo REAL, estado TEXT)''')
        # Historial de ventas diarias
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

# --- SISTEMA DE IMPRESIÓN ---
def imprimir_ticket(html):
    comp_id = str(uuid.uuid4())[:8]
    script = f"""
    <div id="print-{comp_id}" style="display:none;">{html}</div>
    <script>
        var content = document.getElementById('print-{comp_id}').innerHTML;
        var win = window.open('', 'PRINT', 'height=600,width=400');
        win.document.write('<html><head><title>Ticket Pastelería</title></head><body>' + content + '</body></html>');
        win.document.close();
        win.focus();
        setTimeout(function() {{ win.print(); win.close(); }}, 500);
    </script>
    """
    components.html(script, height=0)

def gen_ticket_html(tipo, folio, detalle, total, saldo=0):
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""
    <div style="font-family: 'monospace'; width: 260px; padding: 15px; border: 1px solid #000; background: #fff; color: #000;">
        <center>
            <h2 style="margin:0;">🍰 SWEET LOGIC</h2>
            <p style="font-size:12px;">Pastelería Artesanal</p>
        </center>
        <hr>
        <p style="font-size:12px;"><b>{tipo}</b>: #{folio}<br><b>Fecha:</b> {fecha}</p>
        <table style="width:100%; font-size:12px;">
            {detalle}
        </table>
        <hr>
        <p align="right"><b>TOTAL: ${total:,.2f}</b></p>
        {f'<p align="right" style="color:red;">RESTANTE: ${saldo:,.2f}</p>' if saldo > 0 else ''}
        <center><p style="font-size:10px;">¡Gracias por endulzar su día!</p></center>
    </div>
    """

# --- INICIALIZACIÓN ---
st.set_page_config(page_title="SweetLogic Pastelería", layout="wide")
init_db()

if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'ticket_ready' not in st.session_state: st.session_state.ticket_ready = None

if st.session_state.ticket_ready:
    imprimir_ticket(st.session_state.ticket_ready)
    st.session_state.ticket_ready = None

# --- MENÚ LATERAL ---
st.sidebar.title("🧁 Panel de Control")
opcion = st.sidebar.radio("Navegación", ["🧁 Vitrina", "📅 Pedidos Especiales", "💰 Caja y Ventas", "⚙️ Admin"])

# --- 1. VITRINA (VENTA RÁPIDA) ---
if opcion == "🧁 Vitrina":
    st.header("Venta de Mostrador")
    df_v = get_df("SELECT * FROM vitrina WHERE stock > 0")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if not df_v.empty:
            prod_sel = st.selectbox("Seleccione Producto", df_v['producto'].unique())
            sabores = df_v[df_v['producto'] == prod_sel]
            sab_sel = st.selectbox("Sabor/Variante", sabores['sabor'])
            
            item = df_v[(df_v['producto'] == prod_sel) & (df_v['sabor'] == sab_sel)].iloc[0]
            st.info(f"Disponible: {item['stock']} unidades | Precio: ${item['precio']}")
            
            cant = st.number_input("Cantidad", 1, int(item['stock']))
            if st.button("➕ Agregar a la orden", use_container_width=True):
                st.session_state.carrito.append({
                    'id': item['id'], 'desc': f"{item['producto']} ({item['sabor']})",
                    'cant': cant, 'precio': item['precio'], 'subtotal': cant * item['precio']
                })
                st.rerun()
    
    with col2:
        if st.session_state.carrito:
            st.subheader("Orden Actual")
            df_car = pd.DataFrame(st.session_state.carrito)
            st.table(df_car[['desc', 'cant', 'subtotal']])
            total = df_car['subtotal'].sum()
            
            if st.button(f"✅ Cobrar ${total:,.2f}", type="primary", use_container_width=True):
                folio = str(uuid.uuid4())[:6].upper()
                detalle_html = ""
                for i in st.session_state.carrito:
                    run_query("UPDATE vitrina SET stock = stock - ? WHERE id = ?", (i['cant'], i['id']))
                    detalle_html += f"<tr><td>{i['desc']}</td><td align='right'>x{i['cant']}</td><td align='right'>${i['subtotal']:.2f}</td></tr>"
                
                run_query("INSERT INTO ventas VALUES (?,?,?,?)", (folio, datetime.now().strftime("%Y-%m-%d"), str(st.session_state.carrito), total))
                st.session_state.ticket_ready = gen_ticket_html("VENTA MOSTRADOR", folio, detalle_html, total)
                st.session_state.carrito = []
                st.rerun()
            
            if st.button("❌ Cancelar orden"):
                st.session_state.carrito = []
                st.rerun()

# --- 2. PEDIDOS ESPECIALES ---
elif opcion == "📅 Pedidos Especiales":
    st.header("Gestión de Pedidos a Futuro")
    
    with st.form("nuevo_pedido"):
        c1, c2 = st.columns(2)
        cliente = c1.text_input("Nombre del Cliente")
        entrega = c2.date_input("Fecha de Entrega", min_value=datetime.now())
        desc = st.text_area("Descripción del Pastel (Sabor, decoración, mensaje)")
        t1, t2 = st.columns(2)
        total_p = t1.number_input("Costo Total", min_value=0.0)
        anticipo = t2.number_input("Anticipo", min_value=0.0)
        
        if st.form_submit_button("🔨 Registrar Pedido"):
            p_id = "ORD-" + str(uuid.uuid4())[:5].upper()
            run_query("INSERT INTO pedidos VALUES (?,?,?,?,?,?,?)", 
                      (p_id, cliente, str(entrega), desc, total_p, anticipo, "PENDIENTE"))
            
            det = f"<tr><td colspan='2'>{desc}</td><td align='right'>${total_p:.2f}</td></tr>"
            st.session_state.ticket_ready = gen_ticket_html("ORDEN DE PEDIDO", p_id, det, total_p, (total_p - anticipo))
            st.success("Pedido guardado e imprimiendo comprobante...")
            st.rerun()

    st.subheader("Pedidos para los próximos 7 días")
    prox = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    df_p = get_df("SELECT * FROM pedidos WHERE fecha_entrega <= ? AND estado = 'PENDIENTE' ORDER BY fecha_entrega ASC", (prox,))
    st.dataframe(df_p, use_container_width=True)

# --- 3. CAJA Y VENTAS ---
elif opcion == "💰 Caja y Ventas":
    st.header("Corte de Caja Diario")
    hoy = datetime.now().strftime("%Y-%m-%d")
    
    v_mostrador = get_df("SELECT SUM(total) as t FROM ventas WHERE fecha = ?", (hoy,)).iloc[0]['t'] or 0
    v_pedidos = get_df("SELECT SUM(anticipo) as t FROM pedidos WHERE substr(id,1,3)='ORD'").iloc[0]['t'] or 0 # Simplificado
    
    m1, m2 = st.columns(2)
    m1.metric("Ventas Mostrador (Hoy)", f"${v_mostrador:,.2f}")
    m2.metric("Total en Caja (Estimado)", f"${(v_mostrador + v_pedidos):,.2f}")
    
    st.subheader("Detalle de Ventas")
    st.dataframe(get_df("SELECT * FROM ventas ORDER BY id DESC"), use_container_width=True)

# --- 4. ADMIN ---
elif opcion == "⚙️ Admin":
    st.header("Configuración de Inventario")
    with st.form("add_vitrina"):
        st.write("Añadir producto a vitrina")
        c1, c2, c3 = st.columns(3)
        p = c1.text_input("Producto (ej. Cheesecake)")
        s = c2.text_input("Sabor (ej. Frutos Rojos)")
        por = c3.number_input("Porciones", 1)
        c4, c5 = st.columns(2)
        stk = c4.number_input("Stock Inicial", 1)
        prc = c5.number_input("Precio Venta", 10.0)
        
        if st.form_submit_button("Guardar en Vitrina"):
            run_query("INSERT OR REPLACE INTO vitrina VALUES (?,?,?,?,?,?)", 
                      (str(uuid.uuid4())[:8], p, s, por, stk, prc))
            st.success("Producto agregado.")
            st.rerun()
    
    if st.button("📥 Exportar Base de Datos"):
        with open(DB_NAME, "rb") as f:
            st.download_button("Descargar .db", f, file_name="respaldo_pasteleria.db")pip