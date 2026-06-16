# processors/working_age_calculator.py
import pandas as pd

def calculate_population_differences(state_data, mun_data, age_cols):
    """
    Recibe los datos aislados de 1 Estado y sus Municipios.
    Suma las edades seleccionadas y resta el fuera de rango.
    """
    cols = list(state_data.columns)
    code_col = cols[0]
    name_col = cols[1]
    
    # Combinar ambos para limpieza masiva
    df_combined = pd.concat([state_data, mun_data])
    
    # Limpieza de comas y conversión a numérico
    for col in age_cols + ['Total']:
        if col in df_combined.columns:
            df_combined[col] = df_combined[col].astype(str).str.replace(',', '', regex=False)
            df_combined[col] = pd.to_numeric(df_combined[col], errors='coerce').fillna(0)
            
    # Cálculos principales
    df_combined['In_Range'] = df_combined[age_cols].sum(axis=1)
    df_combined['Out_Of_Range'] = df_combined['Total'] - df_combined['In_Range']
    
    # Separar de nuevo
    state_clean = df_combined[df_combined[code_col].str.len() == 2]
    mun_clean = df_combined[df_combined[code_col].str.len() == 5]
    
    state_in = state_clean['In_Range'].values[0] if not state_clean.empty else 0
    state_out = state_clean['Out_Of_Range'].values[0] if not state_clean.empty else 0
    
    results = []
    
    # Iterar solo sobre los municipios del estado seleccionado
    for _, mun_row in mun_clean.iterrows():
        mun_in = mun_row['In_Range']
        mun_out = mun_row['Out_Of_Range']
        diff_out_range = state_out - mun_out
        
        results.append({
            'Cód. Mpio': mun_row[code_col],
            'Municipio': mun_row[name_col],
            'Mpio. En Rango': mun_in,
            'Mpio. Fuera Rango': mun_out,
            'Estado En Rango': state_in,
            'Estado Fuera Rango': state_out,
            'Resta (Estado - Mpio)': diff_out_range
        })
        
    return pd.DataFrame(results)