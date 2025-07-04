import streamlit as st
import pandas as pd
import sqlite3

st.set_page_config(page_title="Analytik Dashboard", layout="wide")
st.title("📊 Analytik | Dashboard Comercial")

@st.cache_data
def cargar_datos():
    conn = sqlite3.connect("almacen_datos.db")  # Cambio clave: ruta relativa
    df = pd.read_sql_query("SELECT * FROM ventas", conn)
    conn.close()
    return df

df = cargar_datos()
df.columns = df.columns.str.strip()

# Validaciones mínimas
required_cols = ["Monto Neto", "Razon Social", "Fecha Docto"]
if not all(col in df.columns for col in required_cols):
    st.error("❌ El archivo no contiene todas las columnas necesarias.")
    st.stop()

# Preparar fecha y columnas temporales
df["Fecha Docto"] = pd.to_datetime(df["Fecha Docto"], errors="coerce")
df = df[df["Fecha Docto"].notna()]
df["Año"] = df["Fecha Docto"].dt.year
df["MesNum"] = df["Fecha Docto"].dt.month

meses_es = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
df["MesNombre"] = df["MesNum"].apply(lambda x: meses_es[x - 1])

# 🎛️ Filtros
st.sidebar.title("🔎 Filtros")
filtros = {
    "Vendedor": st.sidebar.multiselect("Vendedor", df["Vendedor"].dropna().unique(), default=None),
    "Razon Social": st.sidebar.multiselect("Cliente", df["Razon Social"].dropna().unique(), default=None),
    "Año": st.sidebar.multiselect("Año", sorted(df["Año"].dropna().unique()), default=None),
    "Mes": st.sidebar.multiselect("Mes", meses_es, default=meses_es),
    "Top N clientes": st.sidebar.slider("📌 Top N Clientes", 3, 30, 10)
}

# Aplicar filtros
df_filtrado = df.copy()
if filtros["Vendedor"]:
    df_filtrado = df_filtrado[df_filtrado["Vendedor"].isin(filtros["Vendedor"])]
if filtros["Razon Social"]:
    df_filtrado = df_filtrado[df_filtrado["Razon Social"].isin(filtros["Razon Social"])]
if filtros["Año"]:
    df_filtrado = df_filtrado[df_filtrado["Año"].isin(filtros["Año"])]
if filtros["Mes"]:
    df_filtrado = df_filtrado[df_filtrado["MesNombre"].isin(filtros["Mes"])]

# 📊 KPIs: comparativa Año vs Año anterior
st.subheader("📈 Indicadores principales")

años_ordenados = sorted(df_filtrado["Año"].dropna().unique())
if len(años_ordenados) >= 2:
    actual, anterior = años_ordenados[-1], años_ordenados[-2]
    df_actual = df_filtrado[df_filtrado["Año"] == actual]
    df_anterior = df_filtrado[df_filtrado["Año"] == anterior]

    ventas_actual = df_actual["Monto Neto"].sum()
    ventas_anterior = df_anterior["Monto Neto"].sum()
    delta_pct = round(((ventas_actual - ventas_anterior) / ventas_anterior * 100), 1) if ventas_anterior else None

    cli_actual = df_actual["Razon Social"].nunique()
    cli_anterior = df_anterior["Razon Social"].nunique()
    delta_cli = round(((cli_actual - cli_anterior) / cli_anterior * 100), 1) if cli_anterior else None

    ticket_actual = ventas_actual / cli_actual if cli_actual else 0
    ticket_anterior = ventas_anterior / cli_anterior if cli_anterior else 0
    delta_ticket = round(((ticket_actual - ticket_anterior) / ticket_anterior * 100), 1) if ticket_anterior else None
else:
    actual = años_ordenados[-1] if años_ordenados else "-"
    ventas_actual, cli_actual, ticket_actual = 0, 0, 0
    delta_pct = delta_cli = delta_ticket = None

col1, col2, col3 = st.columns(3)
col1.metric(f"💰 Ventas {actual}", f"${ventas_actual:,.0f}",
            f"{delta_pct:+.1f}%" if delta_pct is not None else "Sin comparación",
            delta_color="inverse" if delta_pct is not None and delta_pct < 0 else "normal")

col2.metric(f"👥 Clientes {actual}", cli_actual,
            f"{delta_cli:+.1f}%" if delta_cli is not None else "Sin comparación",
            delta_color="inverse" if delta_cli is not None and delta_cli < 0 else "normal")

col3.metric("🎟️ Ticket Promedio", f"${ticket_actual:,.0f}",
            f"{delta_ticket:+.1f}%" if delta_ticket is not None else "Sin comparación",
            delta_color="inverse" if delta_ticket is not None and delta_ticket < 0 else "normal")

# 🏢 Top N Clientes
st.subheader(f"🏢 Top {filtros['Top N clientes']} Clientes por ventas")
top_clientes = (
    df_filtrado.groupby("Razon Social")["Monto Neto"]
    .sum()
    .sort_values(ascending=False)
    .head(filtros["Top N clientes"])
)
st.bar_chart(top_clientes)

# 📆 Evolución mensual
st.subheader("📆 Evolución mensual de ventas")
evolucion = df_filtrado.groupby(["Año", "MesNum"])["Monto Neto"].sum().reset_index()
evolucion["FechaEje"] = pd.to_datetime(evolucion["Año"].astype(str) + "-" + evolucion["MesNum"].astype(str) + "-01")
evolucion = evolucion.sort_values("FechaEje")

if len(años_ordenados) == 1:
    evolucion["Etiqueta"] = evolucion["MesNum"].apply(lambda x: meses_es[x - 1])
else:
    evolucion["Etiqueta"] = evolucion["MesNum"].apply(lambda x: meses_es[x - 1]) + " " + evolucion["Año"].astype(str)

if not evolucion.empty:
    st.line_chart(evolucion.set_index("FechaEje")["Monto Neto"])
    mes_max = evolucion.loc[evolucion["Monto Neto"].idxmax()]
    st.success(f"📈 Pico de ventas: {mes_max['Etiqueta']} → ${mes_max['Monto Neto']:,.0f}")
else:
    st.info("No hay evolución mensual para mostrar.")

# 📋 Tabla y descarga
st.subheader("📄 Detalle de registros")
st.dataframe(df_filtrado)

st.download_button(
    label="📥 Descargar CSV",
    data=df_filtrado.to_csv(index=False).encode("utf-8"),
    file_name="reporte_comercial.csv",
    mime="text/csv"
)
