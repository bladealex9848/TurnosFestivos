import pandas as pd
import streamlit as st
from datetime import datetime
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

# Configuración de la página de Streamlit para la aplicación de Generador de Turnos
st.set_page_config(
    page_title="Generador de Turnos", 
    page_icon="📅",  # Cambia el ícono según tu preferencia
    initial_sidebar_state='collapsed',
    menu_items={
        'Get Help': 'https://alexander.oviedo.isabellaea.com/',  # Enlace de ayuda, cámbialo según necesites
        'Report a bug': None,  # O un enlace para reportar errores
        'About': "Esta aplicación facilita la generación de turnos, tomando en cuenta días festivos y fines de semana."
    }
)

# Título y presentación de la aplicación
st.title('Generador de Turnos')
st.write("""
Bienvenido al Generador de Turnos. Esta aplicación te permite crear una programación de turnos basada en fechas seleccionadas, 
considerando días festivos y fines de semana. Simplemente carga los archivos necesarios y selecciona el rango de fechas.
""")

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
def obtener_fechas_filtradas(fecha_inicio, fecha_fin, df_festivos):
    fechas = pd.date_range(fecha_inicio, fecha_fin, freq='D').to_pydatetime().tolist()
    fechas_filtradas = [fecha for fecha in fechas if fecha.weekday() >= 5 or fecha.strftime('%Y-%m-%d') in df_festivos['fecha'].values]
    return fechas_filtradas

# Función para generar la etiqueta del día, incluyendo la palabra 'Festivo' si es necesario
def etiquetar_dia(fecha, df_festivos):
    nombre_dia = days_translation[fecha.strftime('%A')]
    es_festivo = fecha.strftime('%Y-%m-%d') in df_festivos['fecha'].values
    return f"{nombre_dia}{' Festivo' if es_festivo else ''}"

# Cargar archivos
uploaded_festivos = st.file_uploader("Cargar archivo de festivos (CSV)", type=['csv'])
uploaded_despachos_apoyo = st.file_uploader("Cargar archivo de despachos y apoyo (CSV)", type=['csv'])
uploaded_codigos = st.file_uploader("Cargar archivo de códigos de despachos y apoyo (XLSX)", type=['xlsx'])

# Seleccionar fechas de inicio y fin
fecha_inicio = st.date_input("Selecciona la fecha de inicio", datetime.today())
fecha_fin = st.date_input("Selecciona la fecha de fin", datetime.today())

# Generar turnos
if st.button('Generar Turnos'):
    if uploaded_festivos and uploaded_despachos_apoyo and uploaded_codigos and fecha_inicio and fecha_fin:
        try:
            # Leer archivos
            df_festivos = pd.read_csv(uploaded_festivos)
            df_despachos_apoyo = pd.read_csv(uploaded_despachos_apoyo, sep=';')
            df_codigos = pd.read_excel(uploaded_codigos)

            # Mapear códigos a nombres
            codigo_a_nombre = dict(zip(df_codigos['Código'], df_codigos['Despacho o Dependencia']))

            # Convertir las fechas de inicio y fin a datetime
            fecha_inicio = pd.to_datetime(fecha_inicio)
            fecha_fin = pd.to_datetime(fecha_fin)

            # Obtener fechas filtradas
            fechas_filtradas = obtener_fechas_filtradas(fecha_inicio, fecha_fin, df_festivos)

            # Crear turnos con códigos y nombres
            turnos_codigos = []
            turnos_nombres = []

            # Se establece el ciclo completo basado en el número de despachos
            ciclo_completo = len(df_despachos_apoyo)  # o df_despachos si estás usando eso

            # Inicializa orden_actual
            orden_actual = 1
            for fecha in fechas_filtradas:
                nombre_dia = etiquetar_dia(fecha, df_festivos)

                # Este índice se usará para rotar a través de los despachos
                index = (orden_actual - 1) % ciclo_completo
                row = df_despachos_apoyo.iloc[index]  # o df_despachos si estás usando eso

                codigo_despacho = row['codigo_despacho']
                codigo_apoyo = row['codigo_despacho_apoyo']

                turno_codigo = {
                    'ORDEN': orden_actual,
                    'FECHA': fecha.strftime('%d/%m/%Y'),
                    'DIA': nombre_dia,
                    'DESPACHO': codigo_despacho,
                    'TURNO DE APOYO': codigo_apoyo
                }
                turno_nombre = {
                    'ORDEN': orden_actual,
                    'FECHA': fecha.strftime('%d/%m/%Y'),
                    'DIA': nombre_dia,
                    'DESPACHO': codigo_a_nombre.get(codigo_despacho, 'Desconocido'),
                    'TURNO DE APOYO': codigo_a_nombre.get(codigo_apoyo, 'Desconocido')
                }
                turnos_codigos.append(turno_codigo)
                turnos_nombres.append(turno_nombre)

                # Incrementa orden_actual y reinícialo si es necesario
                orden_actual = (orden_actual % ciclo_completo) + 1

            # Convertir a DataFrame
            df_turnos_codigos = pd.DataFrame(turnos_codigos)
            df_turnos_nombres = pd.DataFrame(turnos_nombres)

            # Preparar el archivo Excel con múltiples hojas
            excel_bytes = BytesIO()
            with pd.ExcelWriter(excel_bytes, engine='xlsxwriter') as writer:
                df_turnos_codigos.to_excel(writer, sheet_name='Turnos_Codigos', index=False)
                df_turnos_nombres.to_excel(writer, sheet_name='Turnos_Nombres', index=False)
            excel_bytes.seek(0)

            # Zip the Excel file before downloading
            zip_buffer = BytesIO()
            with ZipFile(zip_buffer, 'a', ZIP_DEFLATED) as zf:
                zf.writestr('turnos.xlsx', excel_bytes.getvalue())
            zip_buffer.seek(0)

            # Descargar el archivo ZIP
            st.download_button(
                label="Descargar turnos como Excel",
                data=zip_buffer.getvalue(),
                file_name='turnos.zip',
                mime='application/zip'
            )
            
            # Mostrar el DataFrame en Streamlit (opcional)
            st.dataframe(df_turnos_nombres[['ORDEN', 'FECHA', 'DIA', 'DESPACHO', 'TURNO DE APOYO']])
        except Exception as e:
            st.error(f'Error al procesar los archivos: {e}')
    else:
        st.error('Por favor, carga todos los archivos y selecciona las fechas.')
        
# Footer
st.sidebar.markdown('---')
st.sidebar.subheader('Creado por:')
st.sidebar.markdown('Alexander Oviedo Fadul')
st.sidebar.markdown("[GitHub](https://github.com/bladealex9848) | [Website](https://alexander.oviedo.isabellaea.com/) | [Instagram](https://www.instagram.com/alexander.oviedo.fadul) | [Twitter](https://twitter.com/alexanderofadul) | [Facebook](https://www.facebook.com/alexanderof/) | [WhatsApp](https://api.whatsapp.com/send?phone=573015930519&text=Hola%20!Quiero%20conversar%20contigo!%20)")