# processors/location_manager.py
import pandas as pd

def clean_geographic_data(df):
    df_clean = df.copy()
    
    # Ahora usamos nombres fijos garantizados por file_manager
    code_col = 'Codigo'
    name_col = 'Entidad_Municipio'
    
    # Destruir espacios en blanco iniciales/finales
    df_clean[code_col] = df_clean[code_col].astype(str).str.strip()
    df_clean[name_col] = df_clean[name_col].astype(str).str.strip()
    
    # Exigir estrictamente 2 o 5 números
    valid_rows = df_clean[code_col].str.match(r'^(\d{2}|\d{5})$', na=False)
    
    return df_clean[valid_rows]

def extract_states_dict(df):
    code_col = 'Codigo'
    name_col = 'Entidad_Municipio'
    
    states_df = df[df[code_col].str.len() == 2]
    return dict(zip(states_df[code_col], states_df[name_col]))

def get_state_and_municipalities(df, state_code):
    code_col = 'Codigo'
    state_code = str(state_code).strip()
    
    state_data = df[df[code_col] == state_code]
    mun_data = df[(df[code_col].str.len() == 5) & (df[code_col].str.startswith(state_code))]
    
    return state_data, mun_data