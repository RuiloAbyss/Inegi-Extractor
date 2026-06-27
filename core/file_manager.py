# core/file_manager.py
import os
import platform
import subprocess
import pandas as pd
import re

def open_file_in_system(filepath):
    try:
        if platform.system() == 'Windows': os.startfile(filepath)
        elif platform.system() == 'Darwin': subprocess.call(('open', filepath))
        else: subprocess.call(('xdg-open', filepath))
    except Exception as e:
        print(f"Error al abrir: {e}")

def extract_source_year(filepath):
    """Escanea el pie de página del archivo en crudo para detectar el año del Censo."""
    try:
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        lines = []
        for enc in encodings:
            try:
                with open(filepath, 'r', encoding=enc, errors='ignore') as f:
                    lines = f.readlines()
                break
            except Exception:
                continue
        # Buscar en las últimas 30 líneas la leyenda de la fuente
        for line in reversed(lines[-30:]):
            if 'FUENTE' in line.upper() or 'CENSO' in line.upper():
                match = re.search(r'\b(19|20)\d{2}\b', line)
                if match: return match.group(0)
    except Exception:
        pass
    return "Desconocido"

# ==========================================
# PATRÓN FACTORY PARA LECTURA DE ARCHIVOS
# ==========================================

class BaseParser:
    """Clase abstracta base para los lectores de archivos."""
    def read(self, filepath):
        raise NotImplementedError("El método read() debe ser implementado por la subclase.")

class PopulationParser(BaseParser):
    """Procesador especializado en Censos de Población (Usa la lógica validada asimétrica)."""
    def read(self, filepath):
        if filepath.lower().endswith(('.xlsx', '.xls')):
            df_raw = pd.read_excel(filepath, header=None, names=range(40))
        else:
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
            df_raw = None
            for enc in encodings:
                try:
                    df_raw = pd.read_csv(filepath, header=None, names=range(40), encoding=enc, sep=',', engine='python')
                    break
                except Exception:
                    continue
            if df_raw is None: raise ValueError("No se pudo leer el archivo.")

        header_idx = -1
        for i in range(min(50, len(df_raw))):
            row_str = " ".join([str(val) for val in df_raw.iloc[i].values if pd.notna(val)])
            if 'De 0 a 4' in row_str or 'De 15 a 19' in row_str or 'H001A' in row_str or 'ACTIVIDAD ECON' in row_str.upper():
                header_idx = i
                break
                
        if header_idx == -1: raise ValueError("No se reconoció la estructura de encabezados típica del INEGI.")
            
        headers = []
        for val in df_raw.iloc[header_idx].values:
            val_str = str(val).strip() if pd.notna(val) else ''
            headers.append(val_str if val_str.lower() not in ['nan', 'none', ''] else '')
        
        # Asignación dinámica esquivando columnas que ya tengan nombre (como Año Censal)
        empty_count = 0
        for i in range(len(headers)):
            if headers[i] == '':
                if empty_count == 0: headers[i] = 'Codigo'
                elif empty_count == 1: headers[i] = 'Entidad_Municipio'
                empty_count += 1
                
        df_data = df_raw.iloc[header_idx + 1:].copy()
        if len(headers) > len(df_data.columns): headers = headers[:len(df_data.columns)]
        elif len(headers) < len(df_data.columns): headers.extend([f"Extra_{i}" for i in range(len(df_data.columns) - len(headers))])
            
        df_data.columns = headers
        df_data.dropna(axis=1, how='all', inplace=True)
        return df_data

class EconomicParser(BaseParser):
    """Procesador especializado en el SAIC / Censos Económicos de alto volumen."""
    def read(self, filepath):
        if filepath.lower().endswith(('.xlsx', '.xls')):
            df_raw = pd.read_excel(filepath, header=None)
            header_idx = -1
            for i in range(min(500, len(df_raw))):
                row_str = " ".join([str(val) for val in df_raw.iloc[i].values if pd.notna(val)]).upper()
                if 'H001A' in row_str or 'ACTIVIDAD ECON' in row_str or 'AÑO CENSAL' in row_str:
                    header_idx = i
                    break
            if header_idx == -1: raise ValueError("No se reconoció el encabezado Económico en el Excel.")
            df_data = pd.read_excel(filepath, skiprows=header_idx)
            
        else:
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
            header_idx = -1
            correct_enc = 'utf-8'
            
            for enc in encodings:
                try:
                    with open(filepath, 'r', encoding=enc, errors='ignore') as f:
                        for i in range(1000):
                            line = f.readline()
                            if not line: break
                            if 'H001A' in line.upper() or 'ACTIVIDAD ECON' in line.upper() or 'AÑO CENSAL' in line.upper():
                                header_idx = i
                                correct_enc = enc
                                break
                    if header_idx != -1: break
                except Exception:
                    continue
                    
            if header_idx == -1:
                raise ValueError("No se reconoció el encabezado Económico en el CSV.")
            
            # Motor 'python' con 'skiprows' para evadir cuellos de botella de memoria y basura superior
            df_data = pd.read_csv(filepath, skiprows=header_idx, encoding=correct_enc, engine='python', on_bad_lines='skip')

        # El SAIC viene limpio en estructura de columnas, solo purgamos los vacíos
        df_data.dropna(axis=1, how='all', inplace=True)
        return df_data

class ParserFactory:
    """Fábrica que rutea dinámicamente el archivo al lector adecuado."""
    @staticmethod
    def get_parser(filepath):
        filename = os.path.basename(filepath).upper()
        if 'SAIC' in filename or 'ECON' in filename:
            return EconomicParser()
        else:
            return PopulationParser()

def load_inegi_data(filepath):
    """Punto de entrada generalizado."""
    parser = ParserFactory.get_parser(filepath)
    return parser.read(filepath)