import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
from Utils import *
from datetime import time
from datos import procesar_datos

# Configurar estilo de página ------------------------------------------------------------------------------------------
st.set_page_config(page_title="Análisis de Consumo de Gas", layout="wide", )

#-----------------------------------------------------------------------------------------------------------------------
@st.cache_data(ttl=600)
def carga_datos(tipo,fecha_inicio,fecha_final,table,redownload):
    datos =find_load(tipo=tipo, ini=str(fecha_inicio), fin=str(fecha_final), table=table,
              redownload=redownload, directorio="./data")
    return datos

#-----------------------------------------------------------------------------------------------------------------------
def conversion_energia(df):

    diario_byc = calcular_consumo_diario(df)
    temp_promedio= df["temperatura"].mean()
    presion_promedio=df["presion"].mean()


#-----------------------------------------------------------------------------------------------------------------------
def calcular_consumo_diario(df):
    """
    Calcula el consumo diario a partir de un DataFrame con volumen acumulativo,
    considerando días de 6am a 6am del día siguiente.

    Parámetros:
    - df: DataFrame con columnas 'fecha' y 'vol_corregido'

    Retorna:
    - DataFrame con columnas 'fecha_label' y 'vol_dias'
    """
    df = df.copy()
    df["fecha"] = pd.to_datetime(df["fecha"])

    # Ajustar el día para que empiece a las 6:30 a.m.
    df["fecha_ajustada"] = df["fecha"].apply(
        lambda x: x.date() if x.hour > 6 or (x.hour == 6 and x.minute >= 30)
        else (x - pd.Timedelta(days=1)).date()
    )

    # Calcular consumo diario como diferencia entre último y primero del día ajustado
    consumo_diario = df.groupby("fecha_ajustada").agg(
        vol_dias=("vol_corregido", lambda x: x.iloc[-1] - x.iloc[0])
    ).reset_index()

    # Añadir etiquetas para gráficos
    consumo_diario["fecha"] = pd.to_datetime(consumo_diario["fecha_ajustada"])
    consumo_diario["fecha_label"] = consumo_diario["fecha"].dt.strftime("%d-%m")

    print(consumo_diario)
    return consumo_diario


#-----------------------------------------------------------------------------------------------------------------------

def calcular_consumo_diario_promedio(df):
    """
    Calcula el consumo diario a partir de un DataFrame con volumen acumulativo,
    considerando días de 6am a 6am del día siguiente.

    Parámetros:
    - df: DataFrame con columnas 'fecha' y 'vol_corregido'

    Retorna:
    - DataFrame con columnas 'fecha_label' y 'vol_dias'
    """
    df = df.copy()
    df["fecha"] = pd.to_datetime(df["fecha"])

    # Crear columna de día 6am-6am
    df["fecha_ajustada"] = df["fecha"].apply(
        lambda x: x.date() if x.hour >= 6 else (x - pd.Timedelta(days=1)).date()
    )

    # Calcular consumo diario: último - primero de cada día ajustado
    consumo_diario = df.groupby("fecha_ajustada").agg(
        vol_dias=("vol_corregido", lambda x: x.iloc[-1] - x.iloc[0])
    ).reset_index()

    consumo_diario["fecha"] = pd.to_datetime(consumo_diario["fecha_ajustada"])
    consumo_diario["fecha_label"] = consumo_diario["fecha"].dt.strftime("%d-%m")
    return consumo_diario

def calcular_salud(df, fecha_inicio, fecha_fin):
    """
    Calcula la salud general de los datos en un rango de fechas.

    Parámetros:
    - df: DataFrame con los datos
    - fecha_inicio: Fecha de inicio del análisis
    - fecha_fin: Fecha final del análisis

    Retorna:
    - Porcentaje de salud de los datos
    """
    # Convertir fecha_inicio y fecha_fin a datetime (inicio y fin del día)
    fecha_inicio = datetime.combine(fecha_inicio, time(6, 0, 0))
    fecha_fin = datetime.combine(fecha_fin, time(6, 0, 0)) + timedelta(days=1)

    df = df[(df["fecha"] >= fecha_inicio) & (df["fecha"] <= fecha_fin)].copy()

    dias = (fecha_fin.date() - fecha_inicio.date()).days

    esperados = (dias) * 48
    reales = len(df)
    salud = (reales / esperados) * 100
    return min(salud, 100)


def calcular_salud_por_dia(df, fecha_inicio, fecha_fin):
    """
    Calcula la salud de los datos por día en un rango de fechas,
    considerando un día como el período desde las 6am hasta las 6am del día siguiente.

    Parámetros:
    - df: DataFrame con los datos
    - fecha_inicio: Fecha de inicio del análisis
    - fecha_fin: Fecha final del análisis

    Retorna:
    - Serie con porcentaje de salud por día
    """

    # Convertir fecha_inicio y fecha_fin a datetime con hora 6am
    fecha_inicio = datetime.combine(fecha_inicio, time(6, 0, 0))
    fecha_fin = datetime.combine(fecha_fin, time(6, 0, 0)) + timedelta(days=1)

    # Crear un rango de todas las fechas (de 6am a 6am)
    todas_fechas = pd.date_range(start=fecha_inicio, end=fecha_fin, freq='24h').date

    # Filtrar datos para el rango de fechas solicitado
    df_filtered = df[(df["fecha"] >= fecha_inicio) & (df["fecha"] <= fecha_fin)]


    if df_filtered.empty:
        return pd.Series(index=todas_fechas[:-1], data=0)

    # Crear columna para día de 6am-6am
    df_filtered['fecha_laboral'] = df_filtered['fecha'].apply(
        lambda x: x.date() if x.hour >= 6 else (x - timedelta(days=1)).date()
    )


    # Calcular frecuencia esperada de registros
    registros_esperados = 96

    # Contar registros por día de 6am-6am
    conteo_por_dia = df_filtered.groupby('fecha_laboral').size()
    # Crear serie de salud con todas las fechas, estableciendo 0 para días sin datos
    salud_por_dia = pd.Series(index=todas_fechas[:-1], data=0)

    # Calcular salud: (cantidad real / cantidad esperada) * 100, limitando a 100%
    for fecha in conteo_por_dia.index:
        if fecha in salud_por_dia.index:
            registros_reales = conteo_por_dia[fecha]
            salud = min(100, (registros_reales / registros_esperados) * 100)
            salud_por_dia[fecha] = salud

    return salud_por_dia


def generar_grafico_total(df_byc, df_pisos, fecha_inicio, fecha_fin):
    """
    Genera una gráfica de barras con un line chart de salud de datos en un eje Y secundario.

    Parámetros:
    - df_byc: DataFrame de Baños y Cocina
    - df_pisos: DataFrame de Pisos y Paredes
    - fecha_inicio: Fecha de inicio del análisis
    - fecha_fin: Fecha final del análisis

    Retorna:
    - fig: Figura de Plotly con gráfica de consumo y salud de datos
    """
    # Calcular consumo diario para cada DataFrame
    df_byc_dia = calcular_consumo_diario(df_byc)
    df_pisos_dia = calcular_consumo_diario(df_pisos)

    # Crear rango de fechas completo
    fechas_completas = pd.date_range(start=fecha_inicio, end=fecha_fin)

    # Convertir fecha_label a datetime sin modificar el año
    df_byc_dia['fecha'] = pd.to_datetime(df_byc_dia['fecha'], errors='coerce')
    df_pisos_dia['fecha'] = pd.to_datetime(df_pisos_dia['fecha'], errors='coerce')


    df_byc_dia_completo = pd.DataFrame({
        'fecha': fechas_completas,
        'vol_dias': 0
    })
    df_pisos_dia_completo = pd.DataFrame({
        'fecha': fechas_completas,
        'vol_dias': 0
    })

    # Combinar los datos existentes con el DataFrame completo
    df_byc_dia_completo = df_byc_dia_completo.merge(
        df_byc_dia[['fecha', 'vol_dias']],
        on='fecha',
        how='left'
    )
    df_byc_dia_completo['vol_dias_y'] = df_byc_dia_completo['vol_dias_y'].fillna(0)
    df_byc_dia_completo['vol_dias'] = df_byc_dia_completo['vol_dias_y']
    df_byc_dia_completo = df_byc_dia_completo.drop(columns=['vol_dias_y'])

    df_pisos_dia_completo = df_pisos_dia_completo.merge(
        df_pisos_dia[['fecha', 'vol_dias']],
        on='fecha',
        how='left'
    )
    df_pisos_dia_completo['vol_dias_y'] = df_pisos_dia_completo['vol_dias_y'].fillna(0)
    df_pisos_dia_completo['vol_dias'] = df_pisos_dia_completo['vol_dias_y']
    df_pisos_dia_completo = df_pisos_dia_completo.drop(columns=['vol_dias_y'])

    salud_datos = calcular_salud_por_dia(pd.concat([df_byc, df_pisos]), fecha_inicio, fecha_fin)

    # Crear figura con dos ejes Y
    fig = go.Figure()

    # Agregar barras de consumo (eje Y primario)
    fig.add_trace(go.Bar(
        x=df_byc_dia_completo["fecha"].dt.strftime('%m-%d'),
        y=df_byc_dia_completo["vol_dias"],
        name="ByC",
        marker_color="#05668D",
        text=[f"{v:.0f} M³" if v > 0 else "" for v in df_byc_dia_completo["vol_dias"]],
        textposition='inside',
        insidetextanchor="middle",
        hovertemplate='<b>%{x}</b><br>ByC: %{y} M³<extra></extra>',
    ))

    fig.add_trace(go.Bar(
        x=df_pisos_dia_completo["fecha"].dt.strftime('%m-%d'),
        y=df_pisos_dia_completo["vol_dias"],
        name="PyP",
        marker_color="#F0F3BD",
        text=[f"{v:.0f} M³" if v > 0 else "" for v in df_pisos_dia_completo["vol_dias"]],
        textposition='inside',
        insidetextanchor="middle",
        hovertemplate='<b>%{x}</b><br>PyP: %{y} M³<extra></extra>',
    ))

    # Calcular total diario
    df_total_dia = pd.DataFrame({
        'fecha': fechas_completas,
        'vol_dias': df_byc_dia_completo['vol_dias'] + df_pisos_dia_completo['vol_dias']
    })

    # Agregar línea de salud de datos (eje Y secundario)
    fig.add_trace(go.Scatter(
        x=df_total_dia["fecha"].dt.strftime('%m-%d'),
        y=salud_datos,
        mode="lines+markers",
        name="Salud de Datos",
        yaxis="y2",
        line=dict(color="rgba(255, 0, 0, 0.5)", width=2, dash='dot'),
        marker=dict(
            size=10,
            symbol="diamond",
            color="rgba(255, 0, 0, 0.7)",
            line=dict(width=1, color="darkred")
        ),
        hovertemplate='<b>%{x}</b><br>Salud: %{y:.1f}%<extra></extra>',
    ))

    # Agregar la suma total ENCIMA de la barra de PyP
    fig.add_trace(go.Scatter(
        x=df_total_dia["fecha"].dt.strftime('%m-%d'),
        y=df_total_dia["vol_dias"],
        mode="text",
        text=[f"{v:.0f}" if v > 0 else "" for v in df_total_dia["vol_dias"]],
        textposition="top center",
        showlegend=False,
        textfont=dict(size=12, color="#101255", family="Georgia"),
    ))

    # Actualizar layout con dos ejes Y
    fig.update_layout(
        title="Consumo Diario y Salud de Datos",
        xaxis_title="Fecha",
        yaxis_title="Consumo Diario (M³)",
        yaxis2=dict(
            title="Salud de Datos (%)",
            overlaying="y",
            side="right",
            range=[0, 100],  # Rango de 0 a 100%
            ticksuffix="%",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.1,
            xanchor="center",
            x=0.5,
            itemsizing='constant',
            font=dict(size=10),

        ),
        barmode="relative",
        xaxis=dict(type="category", tickangle=-45, showgrid=False,
                   tickfont=dict(size=14, family="Helvetica", color="gray")),
        yaxis=dict(showgrid=True, gridcolor="lightgrey"),
        font=dict(color='black'),
        hoverlabel=dict(bgcolor='white', font_size=12, font_family='Tahoma'),
        margin=dict(l=40, r=40, t=60, b=80)
    )

    return fig

# ----------------------------------------------------------------------------------------------------------------------

def fluctuacion(df_byc, df_pisos, df_erm, df_interno, df_horno, titulo="", key=None):
    """
    Función para visualizar la fluctuación de gas en diferentes secciones.

    Parámetros:
        df_byc: DataFrame con las columnas 'fecha' y 'vol_corregido' para ByC.
        df_pisos: DataFrame con las columnas 'fecha' y 'vol_corregido' para PyP.
        df_erm: DataFrame con las columnas 'fecha' y 'vol_corregido' para ERM.
        df_interno: DataFrame con las columnas 'fecha' y 'vol_corregido' para Interno.
        df_horno: DataFrame con las columnas 'fecha' y 'vol_corregido' para Horno.
        titulo: Título de la gráfica.
        key: Clave opcional para Streamlit.
    """

    # Calcular la diferencia para detectar fluctuaciones
    for df in [df_byc, df_pisos, df_erm, df_interno, df_horno]:
        # Calcular la diferencia entre vol_corregido
        df["diferencia"] = df["vol_corregido"].diff().fillna(0)

        # Eliminar filas duplicadas basadas en la columna "fecha_ajustada"
        df.drop_duplicates(subset="fecha", keep="first", inplace=True)

    fig = go.Figure()

    # Lista de trazas con colores específicos
    trazas = [
        ("ByC", df_byc, "#05668D", True),   # Activo por defecto
        ("PyP", df_pisos, "#f4e04d", False),
        ("ERM", df_erm, "#02C39A", False),
        ("Interno", df_interno, "#028090", False),
        ("Horno", df_horno, "#00A896", False)
    ]


    for nombre, df, color, visible in trazas:
        fig.add_trace(go.Scatter(
            x=df["fecha"],
            y=df["diferencia"],
            mode="lines",
            name=nombre,
            line=dict(color=color),
            visible=True if visible else "legendonly"
        ))

    fig.update_layout(
        title=titulo,
        xaxis_title="Tiempo",
        yaxis_title="Entrada de gas (M³)",
        template="plotly_white",
        xaxis=dict(showgrid=True)
    )

    st.plotly_chart(fig, key=key)


# ----------------------------------------------------------------------------------------------------------------------

def grafico_consumo_total(df_byc_dia, df_pisos_dia, df_erm_dia, df_interno_dia, df_horno_dia):
    # Calcular el consumo total de cada sección
    consumo_byc = df_byc_dia["vol_dias"].sum()
    consumo_PyP = df_pisos_dia["vol_dias"].sum()
    consumo_erm = df_erm_dia["vol_dias"].sum()
    consumo_interno = df_interno_dia["vol_dias"].sum()
    consumo_horno = df_horno_dia["vol_dias"].sum()

    # Calcular la suma de ByC + Pisos
    consumo_total_byc_PyP = consumo_byc + consumo_PyP

    # Crear figura
    fig_total = go.Figure()

    # Datos para las barras
    secciones = ["ByC", "PyP", "ERM", "Interno", "Horno", "Total"]
    consumos = [consumo_byc, consumo_PyP, consumo_erm, consumo_interno, consumo_horno, consumo_total_byc_PyP]
    colores = ["#05668D", "#F0F3BD", "#02C39A", "#028090", "#00A896", "#34495e"]

    # Agregar las barras al gráfico
    for seccion, consumo, color in zip(secciones, consumos, colores):
        fig_total.add_trace(go.Bar(
            x=[seccion],
            y=[consumo],
            name=seccion,
            marker_color=color,
            text=[f"{consumo:.0f} M³"],
            textposition="inside",
            insidetextanchor="middle"
        ))

    # Configurar el diseño
    fig_total.update_layout(
        title="Consumo Total por Sección",
        xaxis_title="Sección",
        yaxis_title="Consumo Total (M³)",
        xaxis=dict(tickmode="array"),
        showlegend=False,
        template="plotly_white"
    )

    return fig_total

# ----------------------------------------------------------------------------------------------------------------------


def promedio_media_hora(dataframes, titulo,key=None):
    """
    Función para graficar el promedio de consumo de gas por cada media hora para todas las secciones en una sola gráfica.

    Parámetros:
        df_dict: Diccionario con los DataFrames de cada sección.
        titulo: Título de la gráfica.
    """

    fig = go.Figure()

    colores = {
        "Baños y Cocina": "#05668D",
        "PyP": "#F0F3BD",
        "ERM": "#02C39A",
        "Interno": "#028090",
        "Horno 5": "#00A896"
    }

    for nombre, df in dataframes.items():
        df["diferencia"] = df["vol_corregido"].diff()
        df["fecha"] = pd.to_datetime(df["fecha"])
        df["MediaHora"] = df["fecha"].dt.floor("30min").dt.strftime("%H:%M")

        df_media_hora = df.groupby("MediaHora")["diferencia"].mean().reset_index()

        # Orden personalizado dentro del bucle
        orden_personalizado = [
            '06:00', '06:30', '07:00', '07:30',
            '08:00', '08:30', '09:00', '09:30',
            '10:00', '10:30', '11:00', '11:30',
            '12:00', '12:30', '13:00', '13:30',
            '14:00', '14:30', '15:00', '15:30',
            '16:00', '16:30', '17:00', '17:30',
            '18:00', '18:30', '19:00', '19:30',
            '20:00', '20:30', '21:00', '21:30',
            '22:00', '22:30', '23:00', '23:30',
            '00:00', '00:30', '01:00', '01:30',
            '02:00', '02:30', '03:00', '03:30',
            '04:00', '04:30', '05:00', '05:30'
        ]

        df_media_hora["MediaHora"] = pd.Categorical(
            df_media_hora["MediaHora"],
            categories=orden_personalizado,
            ordered=True
        )

        # Es importante ordenar después de asignar la categoría
        df_media_hora = df_media_hora.sort_values("MediaHora")

        fig.add_trace(go.Bar(
            x=df_media_hora["MediaHora"],
            y=df_media_hora["diferencia"],
            name=nombre,
            marker_color=colores[nombre],
            visible=True if nombre == "Baños y Cocina" else "legendonly"
        ))

    fig.update_layout(
        title=titulo,
        xaxis_title="Tiempo",
        yaxis_title="Consumo (M³)",
        template="plotly_white",
        barmode="group"
    )

    st.plotly_chart(fig,key=key)

#------------------------------------------------------------------------------------------------------

def promedio_semana(df, nombre):
    """
    Calcula el promedio de consumo por día de la semana utilizando el método
    calcular_consumo_diario().

    Parámetros:
      - df: DataFrame con columnas 'fecha' y 'vol_corregido'.
      - nombre: Nombre con el que se renombrará la columna de consumo promedio.

    Retorna:
      - DataFrame con columnas 'DiaSemana' y la columna renombrada con el promedio.
    """
    # Se utiliza el método previamente definido para calcular el consumo diario.
    df_diario = calcular_consumo_diario_promedio(df)
    # df_diario tiene columnas: "fecha", "vol_dias" y "fecha_label"

    # Extraer el nombre del día de la semana a partir de "fecha"
    df_diario["DiaSemana"] = df_diario["fecha"].dt.day_name()

    # Calcular el promedio diario por día de la semana
    df_promedio = df_diario.groupby("DiaSemana")["vol_dias"].mean().reset_index()

    # Traducir los nombres de los días al español
    dias_traduccion = {
        "Sunday": "Domingo",
        "Monday": "Lunes",
        "Tuesday": "Martes",
        "Wednesday": "Miércoles",
        "Thursday": "Jueves",
        "Friday": "Viernes",
        "Saturday": "Sábado"
    }

    df_promedio["DiaSemana"] = df_promedio["DiaSemana"].map(dias_traduccion)


    orden_dias = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
    df_promedio["DiaSemana"] = pd.Categorical(df_promedio["DiaSemana"], categories=orden_dias, ordered=True)
    df_promedio = df_promedio.sort_values("DiaSemana")
    # Renombrar la columna de consumo promedio
    df_promedio.rename(columns={"vol_dias": nombre}, inplace=True)
    return df_promedio




# Grafica para promedios_semana -----------------------------------------------------------------------------------------


def generar_grafico(dataframes):
    """Genera una gráfica con los promedios de cada categoría."""
    df_promedios = [promedio_semana(df, nombre) for nombre, df in dataframes.items()]

    # Fusionar todos los DataFrames
    merged_df = df_promedios[0]
    for df in df_promedios[1:]:
        merged_df = merged_df.merge(df, on="DiaSemana")

    columnas_numericas = ["Baños y Cocina", "PyP", "ERM", "Interno", "Horno 5"]
    merged_df = merged_df[(merged_df[columnas_numericas] != 0).any(axis=1)]

    fig = go.Figure()

    colores = {
        "Baños y Cocina": "#05668D",
        "PyP": "#F0F3BD",
        "ERM": "#02C39A",
        "Interno": "#028090",
        "Horno 5": "#00A896",
    }

    for nombre in dataframes.keys():
        fig.add_trace(go.Bar(
            x=merged_df["DiaSemana"],
            y=merged_df[nombre],
            name=nombre,
            marker=dict(color=colores[nombre]),
            text=[f"{v:.0f} M³" for v in merged_df[nombre]],
            textposition="inside",
            insidetextanchor="middle",
            visible=True if nombre == "Baños y Cocina" else "legendonly"
        ))

    return fig
# ---------------------------------------------------------------------------------------------------------------------


def comparar_semanas(df, titulo="Comparación Semanal de Consumo de Gas"):
    # Asegurarse de que la columna "fecha" esté en formato datetime
    df["fecha"] = pd.to_datetime(df["fecha"])

    # Usar el método calcular_consumo_diario para obtener el consumo diario
    df_diario = calcular_consumo_diario(df)

    # Extraer día de la semana y semana (Año-Semana) del DataFrame procesado
    df_diario["DiaSemana"] = df_diario["fecha"].dt.day_name()

    # Mapeo de días de la semana en español
    dias_español = {
        "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
        "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
    }
    df_diario["DiaSemana"] = df_diario["DiaSemana"].map(dias_español)
    df_diario["Semana"] = df_diario["fecha"].dt.strftime("%Y-%U")

    # Mapeo de número de mes a nombre del mes
    meses = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
        7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }

    # Crear un diccionario para mapear semanas a rangos de fechas

    semanas_disponibles = sorted(df_diario["Semana"].unique())
    rango_fechas = {
        semana: f"Semana del {df_diario[df_diario['Semana'] == semana]['fecha'].min().strftime('%d')} de {meses[df_diario[df_diario['Semana'] == semana]['fecha'].min().month]} "
                f"al {df_diario[df_diario['Semana'] == semana]['fecha'].max().strftime('%d')} de {meses[df_diario[df_diario['Semana'] == semana]['fecha'].max().month]}"
        for semana in semanas_disponibles
    }

    # Lista con los rangos formateados
    semanas_mapeadas = [rango_fechas[semana] for semana in semanas_disponibles]

    # Verificar si hay al menos dos semanas disponibles
    if len(semanas_mapeadas) < 2:
        st.warning("⚠ No hay suficientes semanas disponibles para la comparación. Intenta ampliar el rango de fechas.")
        return

    # Definir la semana actual y la anterior como predeterminadas
    semana_actual = semanas_mapeadas[-1]
    semana_anterior = semanas_mapeadas[-2]

    # Inicializar o validar session_state
    if 'semana_1' not in st.session_state or st.session_state.semana_1 not in semanas_mapeadas:
        st.session_state.semana_1 = semana_anterior

    if 'semana_2' not in st.session_state or st.session_state.semana_2 not in semanas_mapeadas:
        st.session_state.semana_2 = semana_actual

    # Obtener índices de forma segura
    index_semana_1 = semanas_mapeadas.index(
        st.session_state.semana_1) if st.session_state.semana_1 in semanas_mapeadas else 0
    index_semana_2 = semanas_mapeadas.index(
        st.session_state.semana_2) if st.session_state.semana_2 in semanas_mapeadas else 1

    # Formulario de selección de semanas
    with st.form(key="formulario_semanas"):
        semana_1 = st.selectbox(
            "Selecciona la primera semana",
            semanas_mapeadas,
            index=index_semana_1,
            key="semana_1"
        )
        semana_2 = st.selectbox(
            "Selecciona la segunda semana",
            semanas_mapeadas,
            index=index_semana_2,
            key="semana_2"
        )
        confirmar = st.form_submit_button(label="Confirmar")

    # Graficar automáticamente si las semanas predeterminadas están establecidas o si se presiona confirmar
    if confirmar or (st.session_state.semana_1 == semana_anterior and st.session_state.semana_2 == semana_actual):
        semana_1_original = next(key for key, value in rango_fechas.items() if value == st.session_state.semana_1)
        semana_2_original = next(key for key, value in rango_fechas.items() if value == st.session_state.semana_2)

        df_semanal = df_diario[df_diario["Semana"].isin([semana_1_original, semana_2_original])]

        if df_semanal.empty:
            st.warning("⚠ No hay suficientes datos para la comparación. Intenta ampliar el rango de fechas.")
            return

        # Agrupar por día de la semana y semana
        df_semanal = df_semanal.groupby(["DiaSemana", "Semana"])["vol_dias"].mean().reset_index()

        # Ordenar días de la semana correctamente en español
        orden_dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        df_semanal["DiaSemana"] = pd.Categorical(df_semanal["DiaSemana"], categories=orden_dias, ordered=True)

        # Pivotear para comparación semanal
        df_pivot = df_semanal.pivot(index="DiaSemana", columns="Semana", values="vol_dias")

        # Crear la gráfica con barras
        fig = go.Figure()
        colores = ['#05669D', '#F0F3BD']

        for i, semana in enumerate(df_pivot.columns):
            fig.add_trace(go.Bar(
                x=df_pivot.index,
                y=df_pivot[semana],
                name=f"Semana {semana}",
                marker=dict(color=colores[i], opacity=0.75, line=dict(color='black', width=0.3)),
            ))

        # Configuración de diseño
        fig.update_layout(
            title=titulo,
            xaxis_title="Día de la Semana",
            yaxis_title="Consumo Promedio (M³)",
            barmode="group",
            template="plotly_white",
            font=dict(size=15, family="Arial"),
            legend=dict(title="Semana", orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
            margin=dict(l=40, r=40, t=40, b=40)
        )

        st.plotly_chart(fig)
        st.success(f"Comparando: {st.session_state.semana_1} 🆚 {st.session_state.semana_2}")


#------------------------------------------------------------Grafica promedio -----------------------------------------------------------------

def generar_graficos_promedios(df_byc_dia, df_pisos_dia, df_horno_dia, df_erm_dia, df_interno_dia,tipo,fecha_inicio,fecha_final):
    # Calcular promedios
    diferencia_dias=(fecha_final-fecha_inicio).days
    if tipo == "day_planta":
        promedios = {
            "ByC": df_byc_dia["vol_dias"].sum() ,
            "Pisos": df_pisos_dia["vol_dias"].sum() ,
            "Horno": df_horno_dia["vol_dias"].sum(),
            "ERM": df_erm_dia["vol_dias"].sum(),
            "Interno": df_interno_dia["vol_dias"].sum()
        }
    else:
        promedios = {
            "ByC": df_byc_dia["vol_dias"].sum() / (diferencia_dias + 1 ),
            "Pisos": df_pisos_dia["vol_dias"].sum() / (diferencia_dias + 1 ),
            "Horno": df_horno_dia["vol_dias"].sum() / (diferencia_dias + 1 ),
            "ERM": df_erm_dia["vol_dias"].sum() / (diferencia_dias + 1 ),
            "Interno": df_interno_dia["vol_dias"].sum() / (diferencia_dias + 1 ),
        }
    # Gráfico 1: Promedios Diarios por Planta
    fig1 = go.Figure([
        go.Bar(
            x=["ByC", "PyP"],
            y=[promedios["ByC"], promedios["Pisos"]],
            marker_color=['#05668D', '#F0F3BD'],
            text=[f"{v:.1f} M³" for v in [promedios["ByC"], promedios["Pisos"]]],
            textposition='inside',
            insidetextanchor="middle",
            textfont=dict(size=14)
        )
    ])
    fig1.update_layout(
        title="Promedios Diarios por Planta",
        xaxis_title="Plantas",
        yaxis_title="Consumo Diario promedio (M³)",
        template="plotly_white"
    )

    # Gráfico 2: Promedios Diarios por Medidor
    fig2 = go.Figure([
        go.Bar(
            x=["Horno", "ERM", "Interno"],
            y=[promedios["Horno"], promedios["ERM"], promedios["Interno"]],
            marker_color=['#00A896', '#02C39A', '#028090'],
            text=[f"{v:.1f} M³" for v in [promedios["Horno"], promedios["ERM"], promedios["Interno"]]],
            textposition='inside',
            insidetextanchor="middle",
            textfont=dict(color='white', size=14)
        )
    ])
    fig2.update_layout(
        title="Promedios Diarios por Medidor",
        xaxis_title="Medidores",
        yaxis_title="Consumo Diario promedio (M³)",
        template="plotly_white"
    )

    return fig1, fig2

#----------------------------------------------------- Grafica de temperatura y presion ---------------------------------------------

def temperatura_presion(df, titulo, key=None):
    """
    Función para graficar temperatura y presión en el tiempo.

    Parámetros:
        df: DataFrame con columnas 'fecha', 'temperatura' y 'presion'.
        titulo: Título de la gráfica.
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Graficar temperatura
    fig.add_trace(
        go.Scatter(
            line_shape='spline',
            x=df['fecha'],
            y=df['temperatura'],
            name="Temperatura",
            mode="lines",
            line=dict(color='#3498db')
        ),
        secondary_y=False
    )

    # Graficar presión
    fig.add_trace(
        go.Scatter(
            line_shape='spline',
            x=df['fecha'],
            y=df['presion'],
            name="Presión",
            mode="lines",
            line=dict(color='#e74c3c')
        ),
        secondary_y=True
    )

    # Definir tickvals de temperatura de forma segura
    if not df['temperatura'].dropna().empty:
        min_temp = int(df['temperatura'].dropna().min())
        max_temp = int(df['temperatura'].dropna().max())
        tickvals = list(range(min_temp, max_temp + 1, 2)) if max_temp > min_temp else [min_temp]
    else:
        tickvals = []  # Sin datos de temperatura

    # Configuración de layout
    fig.update_layout(
        title=titulo,
        template="plotly_white",
        xaxis_title="Tiempo",
        yaxis_title="Temperatura (℃)"
    )

    # Configuración de ejes
    fig.update_yaxes(
        title_text="Temperatura (℃)",
        secondary_y=False,
        tickmode="array",
        tickvals=tickvals,
        tickformat=".1f",
        showgrid=True
    )
    fig.update_yaxes(title_text="Presión (mbar)", secondary_y=True)

    return st.plotly_chart(fig, use_container_width=True, key=key)


def mostrar_tabs(data, fecha_inicio, fecha_final, tipo):
    # Tabs --------------------------------------------------------------------------------------------------------------------------------------------------------------------
    tab1, tab2, tab3, tab4, tab5, tab6,tab7 = st.tabs(
        [" ⚡ Indice energetico"," 🔬Análisis", " ⚖️Comparaciones", " ⏳ Consumo por Hora", " 📉Fluctuación"," 🔥Temperatura y Presión",
         " 🧩Dataframes"])

    df_byc = data["byc"]
    df_pisos = data["pisos"]
    df_erm = data["erm"]
    df_interno = data["interno"]
    df_horno = data["horno"]
    df_byc_dia = data["byc_dia"]
    df_pisos_dia = data["pisos_dia"]
    df_erm_dia = data["erm_dia"]
    df_interno_dia = data["interno_dia"]
    df_horno_dia = data["horno_dia"]





    with tab1:
        st.title("M³ ➟ Energia")
        st.divider()
        st.warning("En Producción")


    # tab 1 -------------------------------------------------------------------------------------------------------------------------------------------------------------------
    with tab2:
        dataframes = {
            "Baños y Cocina": df_byc,
            "PyP": df_pisos,
            "ERM": df_erm,
            "Interno": df_interno,
            "Horno 5": df_horno
        }
        st.title("Consumos")
        st.subheader("Consumo Mensual")
        st.plotly_chart(generar_grafico_total(df_byc, df_pisos, fecha_inicio, fecha_final))

        st.subheader("Consumo Total de Gas en el Rango Seleccionado")
        fig_total = grafico_consumo_total(df_byc_dia, df_pisos_dia, df_erm_dia, df_interno_dia, df_horno_dia)
        st.plotly_chart(fig_total, use_container_width=True)

        st.divider()

        st.title("Promedios")
        st.subheader("Promedio Diario de Consumo de Gas ")
        fig1, fig2 = generar_graficos_promedios(df_byc_dia, df_pisos_dia, df_horno_dia, df_erm_dia, df_interno_dia,tipo,fecha_inicio, fecha_final)
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Promedios por Día de la Semana")
        fig = generar_grafico(dataframes)
        st.plotly_chart(fig)

    # tab 2 --------------------------------------------------------------------------------------------------------------------------------------------------------------------
    with tab3:
        st.divider()
        st.subheader("Comparación de Días de Semana")
        if 'comparacion' not in st.session_state:
            st.session_state['comparacion'] = 'Baños y Cocina'

        seccion2 = st.radio("Escoge la sección que quieres comparar",
                            ['Baños y Cocina', 'PyP', 'ERM', 'Interno', 'Horno 5'],
                            key="comparacion")

        seccion2 = st.session_state['comparacion']

        match seccion2:
            case 'Baños y Cocina':
                comparar_semanas(df_byc, 'Comparación de Semanas de Baños y Cocina')
            case 'PyP':
                comparar_semanas(df_pisos, 'Comparación de Semanas de Pisos y Paredes')
            case 'ERM':
                comparar_semanas(df_erm, 'Comparación de Semanas de ERM')
            case 'Interno':
                comparar_semanas(df_interno, 'Comparación de Semanas de Interno')
            case 'Horno 5':
                comparar_semanas(df_horno, 'Comparación de Semanas de Horno 5')

    # tab 3 ------------------------------------------------------- Gráfico del promedio por hora --------------------------------------------------------------------------------------
    with tab4:
        st.title("Consumo por Hora")
        promedio_media_hora(dataframes, "Promedio por Hora de Consumo de Gas")

    # tab 4 ------------------------------------------------------ Fluctuación --------------------------------------------------------------------------------------------------
    with tab5:
        st.title("Fluctuación en el Consumo de Gas")
        fluctuacion(df_byc, df_pisos, df_erm, df_interno, df_horno, "Gráfica de Fluctuación")

    # tab 5 --------------------------------------------------------- Temperatura y Presión ----------------------------------------------------------------------------------------------------------------
    with tab6:
        temperatura_presion(df_interno, "Gráfica de Temperatura y Presión del Medidor Interno")
        temperatura_presion(df_erm, "Gráfica de Temperatura y Presión del Medidor ERM")

    # tab 6 --------------------------------------------------------- Dataframes ----------------------------------------------------------------------------------------------------------------
    with tab7:
        st.title("Dataframes")
        st.divider()
        st.header("Dataframes importados")
        st.subheader("ERM")
        st.dataframe(df_erm)
        st.subheader("Interno")
        st.dataframe(df_interno)
        st.subheader("Horno 5")
        st.dataframe(df_horno)
        st.divider()
        st.header("Dataframes creados")
        st.subheader("Baños y Cocina")
        st.dataframe(df_byc)
        st.subheader("Pisos y Paredes")
        st.dataframe(df_pisos)













