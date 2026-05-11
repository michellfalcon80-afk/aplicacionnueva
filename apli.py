import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# ==========================================
# CAPA DE DATOS (Clase Controladora)
# ==========================================
class DatabaseManager:
    """Clase para encapsular toda la lógica de SQL"""
    def __init__(self, db_name="biblioteca.db"):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_name) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS libros 
                            (id INTEGER PRIMARY KEY AUTOINCREMENT,
                             titulo TEXT NOT NULL,
                             autor TEXT NOT NULL,
                             categoria TEXT,
                             leido BOOLEAN,
                             fecha_agregado TEXT)''')

    def ejecutar(self, query, params=()):
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()

    def obtener_datos(self, query, params=()):
        with sqlite3.connect(self.db_name) as conn:
            return pd.read_sql_query(query, conn, params=params)

# ==========================================
# INTERFAZ DE USUARIO (Streamlit)
# ==========================================
def main():
    st.set_page_config(page_title="Mi Biblioteca", page_icon="📚")
    
    # Inicializamos el gestor de base de datos
    db = DatabaseManager()

    # Título y Estilo
    st.title("📚 Libri-Center")
    st.markdown("---")

    # Sidebar para Navegación
    menu = ["🏠 Inicio", "➕ Agregar Libro", "🔍 Explorar y Editar"]
    choice = st.sidebar.selectbox("Navegación", menu)

    if choice == "🏠 Inicio":
        mostrar_dashboard(db)
    
    elif choice == "➕ Agregar Libro":
        mostrar_formulario_agregar(db)
        
    elif choice == "🔍 Explorar y Editar":
        mostrar_catalogo(db)

# --- VISTA: DASHBOARD ---
def mostrar_dashboard(db):
    st.subheader("Estadísticas de tu Colección")
    df = db.obtener_datos("SELECT * FROM libros")
    
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Libros", len(df))
        c2.metric("Leídos", len(df[df['leido'] == True]))
        c3.metric("Por leer", len(df[df['leido'] == False]))
        
        st.write("### Últimas Adiciones")
        st.table(df.tail(3)[['titulo', 'autor', 'categoria']])
    else:
        st.info("Tu biblioteca está vacía. ¡Empieza agregando un libro!")

# --- VISTA: FORMULARIO ---
def mostrar_formulario_agregar(db):
    st.subheader("Registrar nuevo ejemplar")
    with st.form("nuevo_libro"):
        t = st.text_input("Título del libro")
        a = st.text_input("Autor")
        cat = st.selectbox("Categoría", ["Novela", "Ciencia", "Historia", "Tecnología", "Otro"])
        l = st.checkbox("¿Ya lo leíste?")
        
        if st.form_submit_button("Guardar en Colección"):
            if t and a:
                db.ejecutar("INSERT INTO libros (titulo, autor, categoria, leido, fecha_agregado) VALUES (?,?,?,?,?)",
                           (t, a, cat, l, datetime.now().strftime("%Y-%m-%d")))
                st.success(f"'{t}' ha sido guardado.")
            else:
                st.warning("El título y el autor son obligatorios.")

# --- VISTA: CATÁLOGO (CON FILTROS Y ELIMINACIÓN) ---
def mostrar_catalogo(db):
    st.subheader("Catálogo Completo")
    
    # Filtro dinámico
    filtro = st.text_input("🔍 Buscar por título o autor")
    query = "SELECT * FROM libros"
    if filtro:
        query += f" WHERE titulo LIKE '%{filtro}%' OR autor LIKE '%{filtro}%'"
    
    df = db.obtener_datos(query)
    
    if not df.empty:
        # Mostramos los datos
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Lógica para eliminar
        st.divider()
        st.write("### Acciones Rápidas")
        id_eliminar = st.number_input("ID del libro a eliminar", min_value=1, step=1)
        if st.button("🗑️ Eliminar Libro", type="primary"):
            db.ejecutar("DELETE FROM libros WHERE id = ?", (id_eliminar,))
            st.toast(f"Libro ID {id_eliminar} eliminado.")
            st.rerun()
    else:
        st.write("No se encontraron resultados.")

if __name__ == "__main__":
    main()