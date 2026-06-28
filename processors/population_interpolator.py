# processors/population_interpolator.py
import pandas as pd
import numpy as np

def extrapolate_population_results(df1, df2, y1, y2, target_year_str):
    """
    Toma dos DataFrames limpios (df1=pasado, df2=reciente).
    Cruza exclusivamente por Cód. Mpio e inyecta la extrapolación CAGR.
    Conserva las columnas originales (edades) de df2.
    """
    try: target_year = int(target_year_str)
    except ValueError: target_year = y2
        
    if df1.empty and df2.empty: return pd.DataFrame()
    if df1.empty: return df2.copy()
    if df2.empty: return df1.copy()

    df1_c = df1.copy()
    df2_c = df2.copy()
    
    # Limpieza exhaustiva de claves numéricas para evitar que los cambios 
    # de nombres (ej. Tlaquepaque vs San Pedro Tlaquepaque) rompan la tabla
    df1_c['Cód. Mpio'] = df1_c['Cód. Mpio'].astype(str).str.strip().str.zfill(5)
    df2_c['Cód. Mpio'] = df2_c['Cód. Mpio'].astype(str).str.strip().str.zfill(5)
    
    # Cruzar por Cód. Mpio. Usamos df2_c como base para conservar sus edades
    df_merged = pd.merge(
        df2_c, 
        df1_c[['Cód. Mpio', 'personas en el rango']], 
        on='Cód. Mpio', 
        how='left', 
        suffixes=('', f'_{y1}')
    )
    
    col1 = f'personas en el rango_{y1}'
    col2 = 'personas en el rango'
    
    val1 = pd.to_numeric(df_merged[col1].astype(str).str.replace(',', '', regex=False), errors='coerce').fillna(0).astype(float)
    val2 = pd.to_numeric(df_merged[col2].astype(str).str.replace(',', '', regex=False), errors='coerce').fillna(0).astype(float)
    
    t_diff = float(y2 - y1) if y2 != y1 else 1.0
    t_target = float(target_year - y1)
    
    linear_target = val1 + (val2 - val1) * (t_target / t_diff)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        ratio = val2 / val1
        r_factor = np.power(ratio, 1.0 / t_diff)
        exp_target = val1 * np.power(r_factor, t_target)
        
    valid_exp = (val1 > 0) & (val2 > 0)
    p_target = np.where(valid_exp, exp_target, linear_target)
    p_target = np.maximum(0, p_target)
    
    # Reconstrucción de la tabla final
    df_result = df2_c.copy()
    if 'personas en el rango' in df_result.columns:
        df_result = df_result.drop(columns=['personas en el rango'])
        
    if 'Municipio' in df_result.columns:
        idx = df_result.columns.get_loc('Municipio') + 1
    else:
        idx = 1
        
    # Inyectar las nuevas columnas justo después del nombre del municipio
    df_result.insert(idx, f'Personas en rango ({y1})', val1.astype(int))
    df_result.insert(idx+1, f'Personas en rango ({y2})', val2.astype(int))
    df_result.insert(idx+2, f'Personas en rango (Extrapolado a {target_year})', np.round(p_target).astype(int))
    
    return df_result

def extrapolate_n_value(val1, val2, y1, y2, target_year_str):
    """Aplica la misma lógica exponencial para extrapolar el indicador maestro N."""
    try: target_year = int(target_year_str)
    except ValueError: return val2
    if y1 == y2 or target_year == y2: return val2
    
    t_diff = float(y2 - y1) if y2 != y1 else 1.0
    t_target = float(target_year - y1)
    
    if val1 <= 0 or val2 <= 0:
        return max(0, val1 + (val2 - val1) * (t_target / t_diff))
        
    ratio = val2 / val1
    r_factor = np.power(ratio, 1.0 / t_diff)
    exp_target = val1 * np.power(r_factor, t_target)
    
    return max(0, exp_target)