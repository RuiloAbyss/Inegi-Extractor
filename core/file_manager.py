# core/file_manager.py
import os
import platform
import subprocess
import pandas as pd

def open_file_in_system(filepath):
    """Abre el archivo con el programa predeterminado del sistema operativo."""
    try:
        if platform.system() == 'Windows':
            os.startfile(filepath)
        elif platform.system() == 'Darwin':
            subprocess.call(('open', filepath))
        else:
            subprocess.call(('xdg-open', filepath))
    except Exception as e:
        print(f"Error al abrir el archivo: {e}")

def load_inegi_data(filepath):
    """
    Lector robusto y universal para archivos del INEGI (CSV o Excel).
    Fuerza una lectura de cuadrícula ancha y detecta codificaciones locales.
    """
    # 1. Leer el archivo crudo forzando 30 columnas para evitar que Pandas recorte la información
    if filepath.lower().endswith(('.xlsx', '.xls')):
        df_raw = pd.read_excel(filepath, header=None, names=range(30))
    else:
        # Intentar diferentes codificaciones típicas en México para rescatar las "ñ"
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        df_raw = None
        for enc in encodings:
            try:
                # engine='python' evita errores de tokenización con columnas desalineadas
                df_raw = pd.read_csv(filepath, header=None, names=range(30), encoding=enc, sep=',', engine='python')
                break
            except Exception:
                continue
        if df_raw is None:
            raise ValueError("No se pudo leer el archivo con ninguna codificación conocida.")

    # 2. Buscar dinámicamente la fila que contiene las edades (La fila 8 en tu Excel)
    header_idx = -1
    for i in range(min(50, len(df_raw))):
        # Convertir toda la fila a un string gigante para buscar palabras clave
        row_str = " ".join([str(val) for val in df_raw.iloc[i].values if pd.notna(val)])
        if 'De 0 a 4' in row_str or 'De 15 a 19' in row_str:
            header_idx = i
            break
            
    if header_idx == -1:
        raise ValueError("No se encontró la fila de encabezados de edades en el archivo.")
        
    # 3. Extraer y limpiar los nombres de las columnas
    headers = []
    for val in df_raw.iloc[header_idx].values:
        val_str = str(val).strip() if pd.notna(val) else ''
        if val_str.lower() in ['nan', 'none', '']:
            headers.append('')
        else:
            headers.append(val_str)
    
    # 4. Asignar los nombres a las Columnas A y B (que vienen vacías en el formato original)
    if len(headers) > 0 and headers[0] == '':
        headers[0] = 'Codigo'
    if len(headers) > 1 and headers[1] == '':
        headers[1] = 'Entidad_Municipio'
        
    # 5. Cortar el DataFrame para quedarnos solo con los datos útiles (a partir de la fila 9)
    df_data = df_raw.iloc[header_idx + 1:].copy()
    
    # Asegurar que la cantidad de encabezados coincida con la cantidad de columnas
    if len(headers) > len(df_data.columns):
        headers = headers[:len(df_data.columns)]
    elif len(headers) < len(df_data.columns):
        headers.extend([f"Extra_{i}" for i in range(len(df_data.columns) - len(headers))])
        
    df_data.columns = headers
    # Eliminar columnas sobrantes totalmente vacías que se crearon por el límite de 30
    df_data.dropna(axis=1, how='all', inplace=True)
    
    # 6. Limpieza final de los códigos para el módulo geográfico
    df_data['Codigo'] = df_data['Codigo'].astype(str).str.strip()
    df_data['Entidad_Municipio'] = df_data['Entidad_Municipio'].astype(str).str.strip()
    
    # Filtrar filas vacías o textos de metadatos como "FUENTE: INEGI..."
    invalid_code = df_data['Codigo'].isin(['', 'nan', 'None'])
    invalid_entity = df_data['Entidad_Municipio'].isin(['', 'nan', 'None'])
    is_source = df_data['Codigo'].str.upper().str.contains('FUENTE', na=False) | df_data['Entidad_Municipio'].str.upper().str.contains('FUENTE', na=False)
    
    df_clean = df_data[~(invalid_code & invalid_entity) & ~is_source].copy()
    
    return df_clean