# processors/location_manager.py

import pandas as pd

def clean_geographic_data(df):
    """
    Limpia el DataFrame con una extracción que destruye los espacios en blanco
    usados como separadores de miles (ej. "14 001" -> "14001") y preserva la herencia.
    """
    df_clean = df.copy()
    
    code_col = df_clean.columns[0] 
    name_col = df_clean.columns[1] 
    
    # 1. Limpiar espacios inútiles en los nombres
    df_clean[name_col] = df_clean[name_col].astype(str).str.strip()
    
    # 2. EL DESTRUCTOR DE FORMATOS (Espacios y Comas)
    raw_codes = df_clean[code_col].astype(str)
    
    # Esta línea es la clave: destruye comas Y espacios en blanco dentro del número
    raw_codes = raw_codes.str.replace(r'[\s,]', '', regex=True)
    
    # Destruye decimales fantasma de Pandas (14001.0 -> 14001)
    raw_codes = raw_codes.str.replace(r'\.\d+', '', regex=True)
    
    # Extraemos únicamente los números enteros ya fusionados
    numerics = raw_codes.str.extract(r'^(\d+)$')[0]
    df_clean[code_col] = numerics
    
    # Eliminamos las filas que no eran números
    df_clean = df_clean.dropna(subset=[code_col])
    
    # 3. Rellenar ceros basándose en la longitud (1->01, 1001->01001)
    df_clean[code_col] = df_clean[code_col].apply(
        lambda x: str(x).zfill(2) if len(str(x)) <= 2 else str(x).zfill(5)
    )
    
    # 4. Filtro estricto: Solo dejar Padre (2 cifras) o Hijo (5 cifras)
    valid_rows = df_clean[code_col].str.match(r'^(\d{2}|\d{5})$', na=False)
    
    return df_clean[valid_rows]

def extract_states_dict(df):
    """
    Obtiene los datos padre. Si el número tiene 2 cifras, es el Estado.
    """
    code_col = df.columns[0]
    name_col = df.columns[1]
    
    states_df = df[df[code_col].str.len() == 2]
    
    return dict(zip(states_df[code_col], states_df[name_col]))

def get_state_and_municipalities(df, state_code):
    """
    Detecta los hijos (5 cifras) y los anida a su padre buscando que
    los 2 primeros números coincidan con el Estado.
    """
    code_col = df.columns[0]
    state_code = str(state_code).strip().zfill(2)
    
    # Fila del dato padre (Estado = 2 cifras)
    state_data = df[df[code_col] == state_code]
    
    # Filas hijas (Municipios = 5 cifras anidados a su padre)
    mun_data = df[(df[code_col].str.len() == 5) & (df[code_col].str.startswith(state_code))]
    
    return state_data, mun_data