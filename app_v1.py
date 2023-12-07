import pandas as pd
import streamlit as st
from datetime import datetime
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

# Traducción de los días de la semana al español
days_translation = {
    'Monday': 'Lunes',
    'Tuesday': 'Martes',
    'Wednesday': 'Miércoles',
    'Thursday': 'Jueves',
    'Friday': 'Viernes',
    'Saturday': 'Sábado',
    'Sunday': 'Domingo'
}

# Función para convertir el DataFrame a bytes de un archivo Excel en memoria
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Turnos')
    output.seek(0)
    return output.getvalue()

# Función para obtener fechas filtradas (sábados, domingos y festivos)
# Función para obtener fechas filtradas (sábados, domingos y festivos)
def obtener_fechas_filtradas(fecha_inicio, fecha_fin, df_festivos):
    fechas = pd.date_range(fecha_inicio, fecha_fin, freq='D').to_pydatetime().tolist()
    fechas_filtradas = [fecha for fecha in fechas if fecha.weekday() >= 5 or fecha.strftime('%Y-%m-%d') in df_festivos['fecha'].values]
    return fechas_filtradas

# Aplicación Streamlit
st.title('Generador de Turnos')

# Cargar archivos
uploaded_festivos = st.file_uploader("Cargar archivo de festivos (CSV)", type=['csv'])
uploaded_despachos = st.file_uploader("Cargar archivo de despachos (CSV)", type=['csv'])
uploaded_turnos_apoyo = st.file_uploader("Cargar archivo de turnos de apoyo (CSV)", type=['csv'])

# Seleccionar fechas de inicio y fin
fecha_inicio = st.date_input("Selecciona la fecha de inicio", datetime.today())
fecha_fin = st.date_input("Selecciona la fecha de fin", datetime.today())

# Generar turnos
if st.button('Generar Turnos'):
    if uploaded_festivos and uploaded_despachos and uploaded_turnos_apoyo and fecha_inicio and fecha_fin:
        try:
            # Leer archivos
            df_festivos = pd.read_csv(uploaded_festivos)
            df_despachos = pd.read_csv(uploaded_despachos)
            df_turnos_apoyo = pd.read_csv(uploaded_turnos_apoyo)

            # Convertir las fechas de inicio y fin a datetime
            fecha_inicio = pd.to_datetime(fecha_inicio)
            fecha_fin = pd.to_datetime(fecha_fin)

            # Obtener fechas filtradas
            fechas_filtradas = obtener_fechas_filtradas(fecha_inicio, fecha_fin, df_festivos)

            # Crear un patrón de rotación para los códigos de despacho y turnos de apoyo
            ciclo_completo = len(df_despachos)
            turnos = []
            for idx, fecha in enumerate(fechas_filtradas):
                # Se utiliza el operador de modulo (%) para repetir el patrón
                indice_despacho = idx % ciclo_completo
                indice_apoyo = idx % ciclo_completo

                turno = {
                    'ORDEN': idx + 1,
                    'FECHA': fecha.strftime('%d/%m/%Y'),
                    'DIA': days_translation[fecha.strftime('%A')],
                    'DESPACHO': df_despachos.iloc[indice_despacho]['codigo'],
                    'TURNO DE APOYO': df_turnos_apoyo.iloc[indice_apoyo]['codigo']
                }
                turnos.append(turno)

            # Convertir a DataFrame
            df_turnos = pd.DataFrame(turnos)

            # Asignar el orden correcto a partir del archivo de despachos
            df_turnos['ORDEN'] = (df_turnos.index % ciclo_completo) + 1

            # Crear un objeto BytesIO para el archivo Excel
            excel_bytes = to_excel(df_turnos)

            # Zip the Excel file before downloading
            zip_buffer = BytesIO()
            with ZipFile(zip_buffer, 'a', ZIP_DEFLATED) as zf:
                zf.writestr('turnos.xlsx', excel_bytes)
            zip_buffer.seek(0)

            # Descargar el archivo ZIP
            st.download_button(
                label="Descargar turnos como Excel",
                data=zip_buffer.getvalue(),
                file_name='turnos.zip',
                mime='application/zip'
            )
            
            # Mostrar el DataFrame en Streamlit (opcional)
            st.dataframe(df_turnos)
        except Exception as e:
            st.error(f'Error al procesar los archivos: {e}')
    else:
        st.error('Por favor, carga todos los archivos y selecciona las fechas.')