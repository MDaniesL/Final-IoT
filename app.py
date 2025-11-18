import streamlit as st
import pandas as pd
from influxdb_client import InfluxDBClient
import plotly.express as px
from datetime import datetime, timedelta, time

#  Conexión
INFLUXDB_URL = "https://us-east-1-1.aws.cloud2.influxdata.com"
INFLUXDB_TOKEN = "JcKXoXE30JQvV9Ggb4-zv6sQc0Zh6B6Haz5eMRW0FrJEduG2KcFJN9-7RoYvVORcFgtrHR-Q_ly-52pD7IC6JQ=="
INFLUXDB_ORG = "0925ccf91ab36478"
INFLUXDB_BUCKET = "EXTREME_MANUFACTURING"

client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
query_api = client.query_api()


#  Lectura de datos de ayer
def load_yesterday_data():
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    query = f"""
    from(bucket: "{INFLUXDB_BUCKET}")
        |> range(start: {yesterday}T00:00:00Z, stop: {yesterday}T23:59:59Z)
        |> filter(fn: (r) => r._measurement == "studio-dht22")
        |> filter(fn: (r) => r._field == "temperatura")
    """

    df = query_api.query_data_frame(org=INFLUXDB_ORG, query=query)

    if isinstance(df, list):
        df = pd.concat(df)

    if df.empty:
        return pd.DataFrame()

    df = df[["_time", "_value"]]
    df.rename(columns={"_time": "Tiempo", "_value": "Temperatura"}, inplace=True)
    df["Tiempo"] = pd.to_datetime(df["Tiempo"])

    return df


#  Funciones
def filter_by_time(df, start_t, end_t):
    """Filter yesterday’s data by user-selected time range."""
    mask = (df["Tiempo"].dt.time >= start_t) & (df["Tiempo"].dt.time <= end_t)
    return df.loc[mask]


def midpoint_timestamp(df):
    """Compute midpoint timestamp of selected data."""
    t_min = df["Tiempo"].min()
    t_max = df["Tiempo"].max()
    return t_min + (t_max - t_min) / 2


def temp_status(df):
    """Temperature threshold checking."""
    if df["Temperatura"].max() > 35:
        return "hot"
    elif df["Temperatura"].min() < 10:
        return "cold"
    return "normal"


HOT_IMAGE = "https://static.vecteezy.com/system/resources/thumbnails/045/364/694/small/midsummer-thermometer-icon-high-temperature-thermometer-and-sun-vector.jpg"


COLD_IMAGE = "https://www.durham.ca/en/health-and-wellness/resources/Images/CWIS-Icon.png"


#  Streamlit App Dashboard
st.title("🌡️ Temperatura de Ayer")
st.write("Selecciona rangos horarios para crear ver cómo estuvo la temperatura ayer.")

# Carga los datos de ayer
df_full = load_yesterday_data()
if df_full.empty:
    st.error("No hay datos disponibles para la fecha anterior.")
    st.stop()

# Inicialización del estado
if "graphs" not in st.session_state:
    st.session_state.graphs = []  # holds graph IDs


# Add graph
if st.button("➕ Añadir Gráfico"):
    new_id = len(st.session_state.graphs)
    st.session_state.graphs.append(new_id)


#  Renderizado de gráficos
to_remove = []

for graph_id in st.session_state.graphs:

    st.subheader(f"📈 Gráfico #{graph_id + 1}")

    # Selección de rangos
    col1, col2 = st.columns(2)
    with col1:
        start_time = st.time_input(
            f"Hora de inicio (gráfico {graph_id + 1})",
            value=time(6, 0),
            key=f"start_{graph_id}"
        )
    with col2:
        end_time = st.time_input(
            f"Hora de final (gráfico {graph_id + 1})",
            value=time(18, 0),
            key=f"end_{graph_id}"
        )

    # Filtrado de datos
    df_filtered = filter_by_time(df_full, start_time, end_time)

    if df_filtered.empty:
        st.warning("No hay datos en este rango horario.")
    else:
        # Plot
        fig = px.line(df_filtered, x="Tiempo", y="Temperatura",
                      title=f"Temperatura entre {start_time} y {end_time}")
        st.plotly_chart(fig, use_container_width=True)

        # Middle timestamp
        mid = midpoint_timestamp(df_filtered)
        mid_hour = mid.hour

        # Elección de imagen según la hora
        if 0 <= mid_hour < 6:
            image_url = "https://static.thenounproject.com/png/2166993-200.png"
        elif 6 <= mid_hour < 12:
            image_url = "https://media.istockphoto.com/id/1262293120/vector/coffee-cup-symbol-icon.jpg?s=612x612&w=0&k=20&c=C5VHghz8P7qraOslQk13-_ArDWHzjhm5ARZ8o7CrO6Y="
        elif 12 <= mid_hour < 18:
            image_url = "https://static.vecteezy.com/system/resources/thumbnails/046/619/542/small/sun-icon-design-vector.jpg"
        else:
            image_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQcymBaPvG8cZX9rQ0ftGVkZuAazQxTZkTacw&s"

        # Renderizado de imagen
        st.image(image_url, width=180)


        # Heat / cold image
        status = temp_status(df_filtered)
        if status == "hot":
            st.image(HOT_IMAGE, width=180, caption="⚠️ Muy Caliente")
        elif status == "cold":
            st.image(COLD_IMAGE, width=180, caption="❄️ Muy Frío")

    # Botón de eliminar
    if st.button(f"🗑️ Eliminar gráfico {graph_id + 1}", key=f"remove_{graph_id}"):
        to_remove.append(graph_id)

    st.markdown("---")


# Borrar gráficos marcados para eliminar
if to_remove:
    st.session_state.graphs = [g for g in st.session_state.graphs if g not in to_remove]
    st.rerun()
