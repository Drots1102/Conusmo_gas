
from analisis import *




# -------------------------- Inicio de la aplicacion -------------------
st.image('./imagenes/IOT_COMPLETO.jpg')
st.divider()
st.markdown("<h1 style='text-align: center; color: #101255;'>Análisis de Consumo de Gas</h1>", unsafe_allow_html=True)
st.divider()

df_erm_sql = pd.DataFrame(columns=["fecha", "vol_corregido","flujo_corregido","presion","temperatura"])
df_interno_sql = pd.DataFrame(columns=["fecha", "vol_corregido","flujo_corregido","presion","temperatura"])
df_horno_sql = pd.DataFrame(columns=["fecha", "vol_corregido","flujo_corregido","presion","temperatura"])

df_byc = pd.DataFrame(columns=["fecha", "vol_corregido"])
df_pisos = pd.DataFrame(columns=["fecha", "vol_corregido"])

# --- Definir el rango de fechas ---
fecha_hoy = datetime.today().date()
fecha_inicio_default = fecha_hoy - timedelta(weeks=1)
fecha_min = datetime(2025, 2, 10).date()

with st.form(key="formulario_analisis"):
    # Organizamos las columnas dentro del formulario
    col1, col2, col3, col4 = st.columns([1.7, 3.5, 3, 2])

    with col2:
        prev_tipo = st.session_state.get('prev_tipo', 'day_planta')
        tipo = {
            "por dia": "day_planta",
            "por rango": "rango_planta"
        }[st.radio(
            "***Seleccione el tipo de análisis***",
            ["por dia", "por rango"],
            horizontal=True,
            key='tipo_analisis_radio'
        )]
        if tipo != prev_tipo:
            st.session_state.prev_tipo = tipo

    with col3:
        if tipo == "rango_planta":
            fecha_inicio = st.date_input(
                "**Seleccione la fecha de inicio del análisis**",
                min_value=fecha_min,
                max_value=fecha_hoy,
                value=fecha_inicio_default,
                key='fecha_inicio_rango'
            )
            fecha_final = st.date_input(
                "**Seleccione la fecha final del análisis**",
                min_value=fecha_inicio,
                max_value=fecha_hoy,
                value=fecha_hoy,
                key='fecha_final_rango'
            )
        else:
            fecha_inicio = st.date_input(
                "**Seleccione la fecha del análisis**",
                min_value=fecha_min,
                max_value=fecha_hoy,
                value=fecha_hoy - timedelta(days=1),
                key='fecha_inicio_dia'
            )
            fecha_final = fecha_inicio  # Para análisis de un solo día

    with col4:
        st.write("")

    # Botón para enviar el formulario
    redownload = st.checkbox("Forzar redescarga", False)

    submit_button = st.form_submit_button("🔍 Analizar")

# Ejecutar el análisis únicamente cuando se pulse el botón

if submit_button:
    with st.spinner("Procesando análisis..."):
        if tipo == "rango_planta":
            st.write("Ejecutando análisis desde:", fecha_inicio, "hasta:", fecha_final)
        else:
            st.write("Ejecutando análisis del día ", fecha_final)

        # --- Obtener los datos de SQL ---
        df_erm_sql = carga_datos(tipo, fecha_inicio, fecha_final, "gas_ERM", redownload)
        df_interno_sql = carga_datos(tipo, fecha_inicio, fecha_final, "gas_INT", redownload)
        df_horno_sql = carga_datos(tipo, fecha_inicio, fecha_final, "gas_H5", redownload)


df_erm,df_interno,df_horno,df_byc,df_pisos = procesar_datos(df_erm_sql,df_interno_sql,df_horno_sql,df_byc,df_pisos)

# Guardar los dataframes en session_state para que persistan
st.session_state['df_erm'] = df_erm
st.session_state['df_interno'] = df_interno
st.session_state['df_horno'] = df_horno
st.session_state['df_byc'] = df_byc
st.session_state['df_pisos'] = df_pisos
st.session_state['datos_cargados'] = True

# Verificar si los datos ya están cargados (después de presionar el botón o en recargas)
if 'datos_cargados' in st.session_state and st.session_state['datos_cargados']:
    # Recuperar los dataframes desde session_state
    df_erm = st.session_state['df_erm']
    df_interno = st.session_state['df_interno']
    df_horno = st.session_state['df_horno']
    df_byc = st.session_state['df_byc']
    df_pisos = st.session_state['df_pisos']

# -------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Aplicar la función a cada DataFrame
df_byc_dia = calcular_consumo_diario(df_byc)
df_pisos_dia = calcular_consumo_diario(df_pisos)
df_erm_dia = calcular_consumo_diario(df_erm)
df_interno_dia = calcular_consumo_diario(df_interno)
df_horno_dia = calcular_consumo_diario(df_horno)
#-----------------------------------------------------
df_erm.drop_duplicates(inplace=True)
df_interno.drop_duplicates(inplace=True)
df_horno.drop_duplicates(inplace=True)
df_byc.drop_duplicates(inplace=True)
df_pisos.drop_duplicates(inplace=True)


# Crear DataFrame para la suma total
df = pd.DataFrame(columns=["vol_dias"])
df["vol_dias"] = (
    df_byc_dia["vol_dias"] +
    df_pisos_dia["vol_dias"] +
    df_erm_dia["vol_dias"] +
    df_interno_dia["vol_dias"] +
    df_horno_dia["vol_dias"]
)

# Formatear fechas a "Día-Mes" en cada DataFrame
for df_seccion in [df_byc_dia, df_pisos_dia, df_erm_dia, df_interno_dia, df_horno_dia]:
    df_seccion["fecha_label"] = df_seccion["fecha"].dt.strftime("%d-%m")
    df_seccion["fecha_label"] = pd.Categorical(df_seccion["fecha_label"], ordered=True)

#-------------------------------------------------------------------------------------------------------------------------------------



st.session_state['df_byc']=df_byc
st.session_state['df_pisos']=df_pisos

data = {
    "byc": df_byc,
    "pisos": df_pisos,
    "erm": df_erm,
    "interno": df_interno,
    "horno": df_horno,
    "byc_dia": df_byc_dia,
    "pisos_dia": df_pisos_dia,
    "erm_dia": df_erm_dia,
    "interno_dia": df_interno_dia,
    "horno_dia": df_horno_dia
}


if df_byc.empty:
    st.warning("⚠️ Seleccione datos para analizar ⚠️ ️")

else:
    salud = calcular_salud(df_byc, fecha_inicio, fecha_final)
    st.metric(label="Salud de los Datos", value=f"{salud:.2f}%")
    mostrar_tabs(data, fecha_inicio, fecha_final, tipo)