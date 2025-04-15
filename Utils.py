# MISCELANEA DE FUNCIONES IIOT - CORONA
# SEPTIEMBRE 2024
# ----------------------------------------------------------------------------------------------------------------------
# Libraries
#import datetime
import time
import os
from io import BytesIO

import pandas as pd
import numpy as np
import pyodbc
from sqlalchemy import create_engine, exc, URL, text
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime ,timedelta


# Constantes
DIRECTORIO = './Data/'
QUERY = "SELECT * FROM {}.dbo.{} WHERE fecha like'{}'"
POR_DIA = 'Por día'
POR_RANGO_DIA = 'Por rango de días'

# ----------------------------------------------------------------------------------------------------------------------
### Funciones

## streamlit
def selector_periodo():
    """
    Función que permite seleccionar el periodo de tiempo a analizar\n
    :return sel_fecha: tipo de periodo a analizar
    :return sel_dia: día a analizar en caso de ser unicamente un día
    :return sel_dia_ini: día inicial en caso de ser un rango de días
    :return sel_dia_fin: día final en caso de ser un rango de días
    :return flag_download: flag que indica si se debe descargar nuevamente los datos
    """
    st.subheader("2) Selección de Periodo a Analizar")
    col1, col2 = st.columns(2)
    with col1:
        sel_fecha = st.radio("¿Que periodo de tiempo desea analizar?",
                                (POR_DIA, POR_RANGO_DIA), key="fecha")

        # Descargar nuevamente flag
        flag_download = False

    with col2:
        # Opciones por día
        if sel_fecha == POR_DIA:
            sel_dia = st.date_input("¿Que dia desea analizar?", datetime.date.today(), key="dia")
            if sel_dia > datetime.date.today():
                st.error("Recuerda que el día seleccionado no puede ser superior a la día actual")
                st.stop()
            st.info("Analizaras el día " + str(sel_dia))

            return sel_fecha, sel_dia, None, None, flag_download

        # Opciones por rango de días
        elif sel_fecha == POR_RANGO_DIA:
            sel_dia_ini = st.date_input("Seleccione el día inicial", datetime.date.today() -
                                        datetime.timedelta(days=1), key="dia_ini")
            sel_dia_fin = st.date_input("Seleccione el día final", datetime.date.today(), key="dia_fin")

            if sel_dia_fin <= sel_dia_ini:
                st.error("Recuerda seleccionar una fecha inicial anterior a la fecha final!!!")
                st.stop()
            elif sel_dia_fin > datetime.date.today():
                st.error("Recuerda que la fecha final no puede ser superior a la fecha actual")
                st.stop()
            else:
                st.info("Analizaras un periodo de tiempo de " + str((sel_dia_fin - sel_dia_ini).days + 1) + " días.")
            
            return sel_fecha, None, sel_dia_ini, sel_dia_fin, flag_download


def boton_descarga(df, name, text_dia, tipo='datos'):
    '''
    Funcion para configurar y mostrar botones de descarga.\n
    :param df: dsataframe a descargar como excel.
    :param name: tabla para formar el nombre del archivo 
    :param text_dia: fecha seleccionada para formar el nombre del archivo
    :param tipo: especifica si se descargaran datos crudos o analisis
    '''
    # Converting to csv file
    excel = to_excel(df, name)
    # Button to export the data
    st.download_button(label='📥 Descargar '+tipo+' como un archivo *.xls',
                        data=excel,
                        file_name='IIOT ' + name + ' ' + text_dia +'.xlsx')


def organize_fecha(df):
    '''
    Función que hace el formateo de la columna de fecha de los data frames\n
    :param df: Dataframe con los datos de la base de datos
    :return df: Dataframe con la columna de fecha organizada
    '''
    # Organizar el tema de fecha
    df["fecha"] = pd.to_datetime(df['fecha'], format='%Y-%m-%d', exact=False)
    df["fecha"] = df["fecha"].dt.normalize()
    df['fecha'] += pd.to_timedelta(df["hora"], unit='h')
    df['fecha'] += pd.to_timedelta(df["minuto"], unit='m')
    df['fecha'] += pd.to_timedelta(df["segundo"], unit='s')

    # Separar los años, meses y días
    df["año"] = df["fecha"].dt.year
    df["mes"] = df["fecha"].dt.month
    df["dia"] = df["fecha"].dt.day
    df["ndia"] = df["fecha"].dt.day_name()

    return df

def get_salud(df, datos_dias, periodo = 'day_planta', sel_dia_ini = None, sel_dia_fin = None):
    '''
    Funcion para calcular la salud de los datos descargados desde la base de datos.\n
    :param df: data frame a examinar
    :param datos_dias: cantidad de registros que debe tener el dataframe
    :param periodo: string que especifica si se calculara un dia o un rango de dias
    :param sel_dia_ini: dia inicial en caso de que se examine en rango de dias
    :param sel_dia_fin: dia final en caso de que se examine en rango de dias

    :return salud_list: lista con los datos de salud agrupados por dia
    :return salud_datos: % de salud de los datos general
    '''
    salud_list = []
    if periodo == 'day_planta':
        # Salud dia
        salud_datos = (df.shape[0] / datos_dias) * 100
        salud_list = [np.round(salud_datos, 2)]
    
    else:
        while sel_dia_ini <= sel_dia_fin:
            df_filter = df.loc[(df.index >= str(sel_dia_ini) + ' 06:00:00') &
                            (df.index <= str(sel_dia_ini + datetime.timedelta(days=1)) + ' 05:59:59')]

            salud_dia = np.round((df_filter.shape[0] / datos_dias) * 100, 2)
            salud_list.append(salud_dia)
            # Avanzo un día
            sel_dia_ini = sel_dia_ini + datetime.timedelta(days=1)
        
        salud_datos = sum(salud_list) / len(salud_list)

    return salud_list, salud_datos


def plot_on_off(fig, df, column, legend, rgb, visibility="legendonly", secondary_y=True, axis_y="y2", r=1, c=1):
    '''
    Funcion para activar o desactivar trazos de la grafica
    '''

    fig.add_trace(go.Scatter(x=df.index, y=df[column],
                             fill='tozeroy', mode="lines",
                             fillcolor=rgb,
                             line_color='rgba(0,0,0,0)',
                             legendgroup=legend,
                             showlegend=True,
                             name=legend,
                             yaxis=axis_y,
                             visible=visibility),
                  secondary_y=secondary_y, row=r, col=c)

    return fig


def plot_json(df, title, dict_graficas):
    '''
    funcion para graficar a partir de archivos json.\n
    :param df: pandas dataframe traído de la base de dato SQL
    :param dict_graficas: json/dict con caracteristicas de la grafica.
    
    :return fig: objeto figura para dibujarlo externamente de la función
    '''
    # crear figura y sub plots
    specs = [[{"secondary_y": True}] for _ in range(dict_graficas["rows"])]
    fig = make_subplots(rows=dict_graficas["rows"], cols=1,  specs=specs,
                        shared_xaxes=True, vertical_spacing=0.06,
                        )

    # add trazos on/off
    for trazo in dict_graficas["on/off"]:
        fig = plot_on_off(fig, df, trazo["column"], trazo["legend"], trazo["rgb"],
                        trazo["visibility"], trazo["second_y"], trazo["axis_y"],
                        trazo["r"], trazo["c"])
        
    # add trazos
    for trazo in dict_graficas["trazos"]:
        fig.add_trace(go.Scatter(x=df.index, y=df[trazo["y"]],
                            line=dict(color=trazo["color"], width=trazo["width"], dash=trazo["dash"]),  
                            mode=trazo["mode"], name=trazo["name"],
                            yaxis=trazo["yaxis"], visible=trazo["visible"],
                            ),
                secondary_y=trazo["secondary_y"], row=trazo["row"], col=trazo["col"])

    # Add figure title
    fig.update_layout(height=800, title=title)

    # Template
    fig.layout.template = 'seaborn' 
    fig.update_layout(modebar_add=["v1hovermode", "toggleSpikeLines"])

    return fig
# ----------------------------------------------------------------------------------------------------------------------
## SQL
@st.cache_data(show_spinner=True)
def load_data(folder, filename):
    '''
    Función que carga el archivo csv guardado al conectar con la base de datos y devuelve un dataframe\n
    :param folder: Direccion de la carpeta 
    :param filename: Nombre del archivo

    :return df: Dataframe
    '''
    df = pd.read_csv(folder + filename, )

    return df


def add_day(day, add=1):
    """
    Función agrega o quita dias, teniendo en cuenta inicio de mes e inicio de año\n
    :param day: "2021-02-01"  EN STRING
    :param add: numero de dias a operar
    
    :return ini_date: día entregado en STR
    :return fin_date: día con los días sumados o restados en STR al día ingresado
    """
    l_day_n = [int(x) for x in day.split("-")]
    ini_date = datetime(l_day_n[0], l_day_n[1], l_day_n[2]).date()
    fin_date = ini_date + timedelta(days=add)

    return str(ini_date), str(fin_date)


def descarga_necesaria(filename, filenames,redownload):
    return (filename in filenames and redownload is False)


# No poner cache en esta función para poder cargar los ultimos datos del día.
def find_load(tipo, ini, fin, table, redownload, directorio):
    """
    Función que busca y carga el archivo de datos si este ya ha sido descargado. En caso contrario lo descarga a través
    de la función sql_connet\n
    mejoras futuras: quitar tipo, ini = 0 if ini = 0 . ini = day.
    :param tipo: ["day_planta", "rango_planta"].
    :param ini: día inicial o unico día a analizar en el rango como STR ("2021-12-28").
    :param fin: día final a analizar como STR ("2022-01-01").
    :param database: base de dato a la cual se debe conectar.
    :param table: tabla a la cual se debe conectar.
    :param redownload: TRUE or FALSE statement si es TRUE se omite la parte de buscar el archivo y se descarga nuevamente.
    :param directorio: directorio donde se guardan los archivos.
    
    :return pd_sql: dataframe con los datos buscados o descargados
    """
    # Setting the folder where to search
    directory = directorio + ini[:-3] + '/'
    if not os.path.exists(directory):
        os.makedirs(directory)
    filenames = os.listdir(directory)

    # Crear el nombre del archivo
    filename = 'tabla_' + table + '_' + ini + '.csv'

    if tipo == "day_planta":
        # Añadir print para depuración
        print(f"Debug - Filename: {filename}")
        print(f"Debug - Filenames en directorio: {filenames}")
        print(f"Debug - Descarga necesaria: {descarga_necesaria(filename, filenames, redownload)}")

        if descarga_necesaria(filename, filenames, redownload):
            pd_sql = load_data(folder=directory, filename=filename)
            print(f"Debug - Datos cargados desde archivo: {len(pd_sql)}")
        else:
            pd_sql = sql_connect(day=str(ini), table=table, directorio=directorio)
            print(f"Debug - Datos de SQL: {len(pd_sql)}")

        # Añadir verificación adicional
        if len(pd_sql) == 0:
            print(f"Advertencia: No se encontraron datos para {table} en {ini}")

    elif tipo == "rango_planta":
        # Fecha Inicial
        l_day_n = [int(x) for x in ini.split("-")]
        ini_date = datetime(l_day_n[0], l_day_n[1], l_day_n[2]).date()
        # Fecha Final
        l_day_n = [int(x) for x in fin.split("-")]
        day_date = datetime(l_day_n[0], l_day_n[1], l_day_n[2]).date()

        # Lista df
        lista_concat = list()
        # Recorro los días de ese periodo de tiempo
        while ini_date <= day_date:
            filename = 'tabla_' + table + '_' + str(ini_date) + '.csv'

            if descarga_necesaria(filename, filenames,redownload):
                aux = load_data(folder=directory, filename=filename)
            else:
                aux = sql_connect(day=str(ini_date), table=table, directorio=directorio)


            lista_concat.append(aux)
            # Avanzo un día
            ini_date = ini_date + timedelta(days=1)

        pd_sql = pd.concat(lista_concat)

    return pd_sql


def sql_connect(day, table, directorio):
    """
    Programa que permite conectar con una base de dato del servidor y devuelve la base de dato como un pandas dataframe\n
    :param tipo: ["day_planta", "day"]
    :param day: Día a descargar en  STR ("2021-04-28")
    :param table: tabla a la cual se debe conectar
    :param directorio: directorio donde se guardan los archivos
    
    :return pd_sql: pandas dataframe traído de la base de dato SQL
    """
    # Connection keys
    server = 'db-prd-iotgirardota.database.windows.net'
    username = 'Securityof'
    password = 'vpiDvO3YBzy5KOyF7vOb'
    database = 'iotgirardota'

    # Connecting to the sql database
    connection_str = "DRIVER={ODBC Driver 18 for SQL Server};SERVER=%s;DATABASE=%s;UID=%s;PWD=%s;Encrypt=no" % (server, database, username, password)
    connection_url = URL.create("mssql+pyodbc", query={"odbc_connect": connection_str})

    conn = create_engine(connection_url)
    # ------------------------------------------------------------------------------------------------------------------

    pd_sql = pd.DataFrame()
    print('Consultando tabla: {}...      '.format(table))
    try:
        # Execute the query
        with conn.begin() as connection:
            ini = day
            if isinstance(ini, datetime):
                ini = ini.strftime("%Y-%m-%d")

            ini_dt = datetime.strptime(ini, "%Y-%m-%d")  # Convierte a datetime

            # Explícitamente configuramos las horas para 6am
            ini_con_hora = ini_dt.replace(hour=6, minute=0,second=0)
            fin_con_hora = (ini_dt + timedelta(days=1)).replace(hour=6, minute=10,second=0)

            # Asegúrate de formatear con la hora incluida
            ini_completo = ini_con_hora.strftime("%Y-%m-%d %H:%M:%S")
            fin_completo = fin_con_hora.strftime("%Y-%m-%d %H:%M:%S")

            # Usa directamente las variables en la consulta
            consulta = "SELECT * FROM {}.dbo.{} WHERE fecha >= '{}' AND fecha < '{}'".format(
                database, table, ini_completo, fin_completo
            )

            # Para verificar la consulta (puedes imprimir esto para depuración)
            pd_sql = pd.read_sql_query(consulta, connection)




    except (exc.TimeoutError, pyodbc.OperationalError):
        print("La consulta ha superado el tiempo límite.")
    finally:
        conn.dispose()  # Close the connection

    # Guardando los datos en archivos estaticos, # No guardar datos si el día seleccionado es el día actual del sistema
    if day != str(datetime.today().date()):
        # Checking and creating the folder
        folder = day[:-3]
        if not os.path.exists(directorio + folder):
            os.makedirs(directorio + folder)
        # Saving the raw data
        pd_sql.to_csv(directorio + folder + '/tabla_' + table + '_' + day + '.csv', index=False)

    return pd_sql

def save_log():
    '''
    Función para guardar los logs de los usuarios que ingresan al sistema
    '''
    day = str(datetime.date.today())
    hora = str(datetime.datetime.now().time())
    user = st.session_state.user_state['email']
    
    # Connection keys 
    server = os.environ.get("SERVER")
    username = os.environ.get("USER_SQL")
    password = os.environ.get("PASSWORD")
    database = os.environ.get("DATABASE")

    # Connecting to the sql database
    connection_str = "DRIVER={ODBC Driver 18 for SQL Server};SERVER=%s;DATABASE=%s;UID=%s;PWD=%s;Encrypt=no" % (server, database, username, password)
    connection_url = URL.create("mssql+pyodbc", query={"odbc_connect": connection_str})

    conn = create_engine(connection_url)

    print('Guardando log de usuario...      ')
    try:
        # Execute the query
        with conn.begin() as connection:
            # Usar text() para construir la consulta y parámetros para pasar valores
            # escapear con [] la palabra reservada user de sql
            query = text("""
                INSERT INTO {}.dbo.log_uso (fecha, hora, [user]) 
                VALUES (:fecha, :hora, :usuario)
            """.format(database))

            # Ejecutar la consulta con parámetros
            connection.execute(query, {
                "fecha": day,
                "hora": hora,
                "usuario": user
            })
    finally:
        conn.dispose()
        
def to_excel(df, name):
    """
    Función para agregar los datos a un excel y poder descargarlo\n
    :param df: data frame
    :param name: nombre de la hoja en el excel

    :return file: archivo a descargar
    """
    # Crear objeto BytesIO vacío
    output = BytesIO()

    # Crear objeto ExcelWriter y escribir el DataFrame en la hoja 'BMC_RA'
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, sheet_name=name)

    # Guardar el archivo de Excel
    writer.close()

    # Obtener los datos del archivo Excel y devolverlos
    archivo = output.getvalue()

    return archivo