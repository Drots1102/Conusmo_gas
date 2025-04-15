import pandas as pd
import numpy as np

def procesar_datos(df_erm,df_interno,df_horno,df_byc,df_pisos):
    #Eliminar duplicados ---------------------------------------------------------------------
    df_erm.drop_duplicates(inplace=True)
    df_interno.drop_duplicates(inplace=True)
    df_horno.drop_duplicates(inplace=True)

    df_erm["fecha"] = pd.to_datetime(df_erm["fecha"], errors="coerce")
    df_interno["fecha"] = pd.to_datetime(df_interno["fecha"], errors="coerce")
    df_horno["fecha"] = pd.to_datetime(df_horno["fecha"], errors="coerce")

    # Ordenar los datos por fecha ---------------------------------------------------------------
    df_erm.sort_values(by='fecha', ascending=True, inplace=True)
    df_interno.sort_values(by='fecha', ascending=True, inplace=True)
    df_horno.sort_values(by='fecha', ascending=True, inplace=True)

    df_erm.reset_index(drop=True, inplace=True)
    df_interno.reset_index(drop=True, inplace=True)
    df_horno.reset_index(drop=True, inplace=True)

    # Convertir la ausencia de datos (0) en Nan -------------------------------------------------------------------------------

    df_erm['vol_corregido'] = df_erm['vol_corregido'].replace(0, np.nan)
    df_interno['vol_corregido'] = df_interno['vol_corregido'].replace(0, np.nan)
    df_horno['vol_corregido'] = df_horno['vol_corregido'].replace(0, np.nan)

    df_erm['presion'] = df_erm['presion'].replace(0, np.nan)
    df_interno['presion'] = df_interno['presion'].replace(0, np.nan)
    df_horno['presion'] = df_horno['presion'].replace(0, np.nan)

    df_erm['temperatura'] = df_erm['temperatura'].replace(0, np.nan)
    df_interno['temperatura'] = df_interno['temperatura'].replace(0, np.nan)
    df_horno['temperatura'] = df_horno['temperatura'].replace(0, np.nan)

    # llenar los Na con valores superiores y si no hay con inferiores ---------------------------------------------------------
    df_erm["vol_corregido"] = df_erm["vol_corregido"].ffill().bfill()
    df_interno["vol_corregido"] = df_interno["vol_corregido"].ffill().bfill()
    df_horno["vol_corregido"] = df_horno["vol_corregido"].ffill().bfill()

    df_erm["presion"] = df_erm["presion"].ffill().bfill()
    df_interno["presion"] = df_interno["presion"].ffill().bfill()
    df_horno["presion"] = df_horno["presion"].ffill().bfill()

    df_erm["temperatura"] = df_erm["temperatura"].ffill().bfill()
    df_interno["temperatura"] = df_interno["temperatura"].ffill().bfill()
    df_horno["temperatura"] = df_horno["temperatura"].ffill().bfill()

    df_interno["temperatura"] = df_interno["temperatura"].astype(str)
    df_interno["temperatura"] = df_interno["temperatura"].str.replace(",", ".").astype(float)

    df_erm["temperatura"] = df_erm["temperatura"].astype(str)
    df_erm["temperatura"] = df_erm["temperatura"].str.replace(",", ".").astype(float)

    df_interno["presion"] = df_interno["presion"].astype(str)
    df_interno["presion"] = df_interno["presion"].str.replace(",", ".").astype(float)

    df_erm["presion"] = df_erm["presion"].astype(str)
    df_erm["presion"] = df_erm["presion"].str.replace(",", ".").astype(float)

    # Eliminar los segundos de los registros ------------------------------------------------------------------------------------
    df_erm["fecha"] = pd.to_datetime(df_erm["fecha"], errors="coerce")
    df_erm["fecha"] = df_erm["fecha"].dt.floor("min")
    df_interno["fecha"] = pd.to_datetime(df_interno["fecha"], errors="coerce")
    df_interno["fecha"] = df_interno["fecha"].dt.floor("min")
    df_horno["fecha"] = pd.to_datetime(df_horno["fecha"], errors="coerce")
    df_horno["fecha"] = df_horno["fecha"].dt.floor("min")

    df_byc["fecha"] = df_interno["fecha"]
    df_pisos["fecha"] = df_erm["fecha"]

    df_pisos = df_pisos.sort_values("fecha")
    df_byc = df_byc.sort_values("fecha")

    df_byc["fecha"] = pd.to_datetime(df_byc["fecha"], errors="coerce")
    df_byc = df_byc.dropna(subset=["fecha"])

    df_pisos["fecha"] = pd.to_datetime(df_pisos["fecha"], errors="coerce")
    df_pisos = df_pisos.dropna(subset=["fecha"])

    # Calcular valores de ByC y PyP ----------------------------------------------------------------------------------------------------

    df_byc["vol_corregido"] = df_interno["vol_corregido"] + df_horno["vol_corregido"]
    df_pisos["vol_corregido"] = df_erm["vol_corregido"] - df_interno["vol_corregido"]

    return df_erm , df_interno,df_horno, df_byc, df_pisos