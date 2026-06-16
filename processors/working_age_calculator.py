# processors/working_age_calculator.py

import pandas as pd

def calculate_population_differences(state_data, mun_data, age_cols):
    """
    Retorna un DataFrame con el desglose de los municipios, organizando las columnas
    para colocar la cantidad de personas en rango inmediatamente después del nombre.
    """
    code_col = 'Codigo'
    name_col = 'Entidad_Municipio'
    
    df_combined = pd.concat([state_data, mun_data]).copy()
    
    # Limpieza numérica de comas
    columns_to_clean = list(set(age_cols + ['Total']))
    for col in columns_to_clean:
        if col in df_combined.columns:
            df_combined[col] = df_combined[col].astype(str).str.replace(',', '', regex=False)
            df_combined[col] = pd.to_numeric(df_combined[col], errors='coerce').fillna(0)
            
    # Calcular sumatoria de personas dentro del rango seleccionado
    df_combined['In_Range'] = df_combined[age_cols].sum(axis=1)
    
    # Aislar a los municipios
    mun_clean = df_combined[df_combined[code_col].str.len() == 5]
    
    results = []
    for _, mun_row in mun_clean.iterrows():
        # NUEVO ORDEN: Código -> Municipio -> Cantidad de personas en rango
        row_dict = {
            'Cód. Mpio': mun_row[code_col],
            'Municipio': mun_row[name_col],
            'personas en el rango': mun_row['In_Range']
        }
        
        # Seguido de las columnas de edad desglosadas dinámicamente
        for col in age_cols:
            row_dict[col] = mun_row[col]
            
        results.append(row_dict)
        
    return pd.DataFrame(results)