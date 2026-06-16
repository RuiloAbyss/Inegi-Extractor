# processors/working_age_calculator.py

import pandas as pd

def calculate_population_differences(state_data, mun_data, age_cols):
    """
    Recibe los datos aislados de 1 Estado y sus Municipios.
    Retorna un DataFrame con el desglose de los municipios, incluyendo
    únicamente las columnas de edad admitidas (dentro del rango) y los cálculos de control.
    """
    code_col = 'Codigo'
    name_col = 'Entidad_Municipio'
    
    # Generar una copia limpia para evitar advertencias de asignación de Pandas
    df_combined = pd.concat([state_data, mun_data]).copy()
    
    # Limpieza de comas y conversión a tipo numérico de las columnas seleccionadas y el Total
    columns_to_clean = list(set(age_cols + ['Total']))
    for col in columns_to_clean:
        if col in df_combined.columns:
            df_combined[col] = df_combined[col].astype(str).str.replace(',', '', regex=False)
            df_combined[col] = pd.to_numeric(df_combined[col], errors='coerce').fillna(0)
            
    # Calcular poblaciones de control por cada fila (municipio y estado)
    df_combined['In_Range'] = df_combined[age_cols].sum(axis=1)
    df_combined['Out_Of_Range'] = df_combined['Total'] - df_combined['In_Range']
    
    # Separar el estado de los municipios ya normalizados numéricamente
    state_clean = df_combined[df_combined[code_col].str.len() == 2]
    mun_clean = df_combined[df_combined[code_col].str.len() == 5]
    
    state_out = state_clean['Out_Of_Range'].values[0] if not state_clean.empty else 0
    
    results = []
    for _, mun_row in mun_clean.iterrows():
        # Diccionario estructural base para el registro del municipio
        row_dict = {
            'Cód. Mpio': mun_row[code_col],
            'Municipio': mun_row[name_col]
        }
        
        # INYECCIÓN DINÁMICA: Agregar solo las columnas de edad admitidas por el filtro
        for col in age_cols:
            row_dict[col] = mun_row[col]
            
        # Columnas de síntesis finales añadidas al extremo derecho de la matriz
        mun_in = mun_row['In_Range']
        mun_out = mun_row['Out_Of_Range']
        
        row_dict['Mpio. En Rango'] = mun_in
        row_dict['Resta (Est - Mpio Fuera)'] = state_out - mun_out
        
        results.append(row_dict)
        
    return pd.DataFrame(results)