import streamlit as st
from datetime import date
import pandas as pd
from Utils import *

st.title("Visualización de Datos")


def calcular_consumo_diario(df):
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()

    # Convertir "fecha" a datetime y redondear al minuto (quitando segundos)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["fecha_min"] = df["fecha"].dt.floor("T")  # elimina segundos

    # Calcular la cantidad de minutos transcurridos desde la medianoche
    df["minutos"] = df["fecha_min"].dt.hour * 60 + df["fecha_min"].dt.minute

    # Definir la hora objetivo: 23:30 = 1410 minutos, y el margen de tolerancia (por ejemplo, ±5 minutos)
    target_min = 23 * 60 + 30  # 1410 minutos
    tolerancia = 5

    # Filtrar los registros cuyo tiempo esté dentro del margen de tolerancia
    df_filtrado = df[abs(df["minutos"] - target_min) <= tolerancia].copy()

    # Si no hay datos cercanos a las 23:30, tomar el último valor de cada día
    if df_filtrado.empty:
        df.set_index("fecha", inplace=True)
        df_filtrado = df.resample("D").last().reset_index()

    # Calcular la diferencia de "vol_corregido" para obtener "vol_dias"
    df_filtrado["vol_dias"] = df_filtrado["vol_corregido"].diff()

    # Eliminar el primer registro (NaN) de cada serie diaria
    df_filtrado = df_filtrado.dropna(subset=["vol_dias"])

    # (Opcional) Eliminar las columnas auxiliares utilizadas para el filtrado
    df_filtrado.drop(columns=["fecha_min", "minutos"], errors="ignore", inplace=True)

    return df_filtrado


# Parámetros en Streamlit
tipo = st.radio("Selecciona el tipo de consulta", ["day_planta", "rango_planta"])
ini = st.date_input("Fecha de inicio", date.today())
fin = st.date_input("Fecha de fin", date.today()) if tipo == "rango_planta" else ini
table = st.text_input("Nombre de la tabla", "gas_INT")
redownload = st.checkbox("Forzar redescarga", False)
directorio = "./data"

ini_str = ini.strftime("%Y-%m-%d")
fin_str = fin.strftime("%Y-%m-%d")

# Botón para ejecutar la función
if st.button("Cargar Datos"):
    df = find_load(tipo, str(ini), str(fin), table, redownload, directorio)

    if df.empty:
        st.warning("⚠️ No se encontraron datos.")
    else:
        st.success(f"✅ Se cargaron {len(df)} registros.")
        st.dataframe(df['fecha'])  # Mostrar los datos en Streamlit
        consumo=calcular_consumo_diario(df)
        st.dataframe(consumo)
        print("aqui las columnas")
        print(consumo.columns)







