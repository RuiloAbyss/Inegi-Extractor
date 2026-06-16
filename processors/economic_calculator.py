# processors/economic_calculator.py
import pandas as pd
import re

def _get_mun_col(df):
    """Localiza dinámicamente la columna del Municipio."""
    mun_cols = [c for c in df.columns if 'MUNICIPIO' in str(c).upper()]
    if mun_cols: return mun_cols[0]
    if len(df.columns) > 2: return df.columns[2] 
    return df.columns[0]

def extract_economic_years(df):
    """
    Extrae los años disponibles esquivando el error de 'float' de Pandas.
    Usa un ciclo seguro que convierte explícitamente a texto antes de validar.
    """
    year_cols = [c for c in df.columns if 'AÑO' in str(c).upper() or 'CENSAL' in str(c).upper()]
    if not year_cols: return []
    
    valid_years = set()
    # Ciclo seguro con str() para evitar el error 'float has no attribute isdigit'
    for y in df[year_cols[0]].dropna().unique():
        y_str = str(y).replace('.0', '').strip()
        if y_str.isdigit() and len(y_str) == 4:
            valid_years.add(y_str)
            
    return sorted(list(valid_years), reverse=True)

def extract_economic_municipalities(df):
    """Extrae el catálogo de municipios aislando el código '001' de 'Acatic'."""
    mun_col = _get_mun_col(df)
    mun_dict = {}
    
    for val in df[mun_col].dropna().unique():
        val_str = str(val).strip()
        match = re.match(r'^(\d{3})\s+(.*)$', val_str)
        if match: mun_dict[match.group(1)] = match.group(2).strip()
        
    return mun_dict

def analyze_economic_hierarchy(df, target_municipality=None, target_year=None):
    df_clean = df.copy()
    
    year_cols = [c for c in df_clean.columns if 'AÑO' in str(c).upper() or 'CENSAL' in str(c).upper()]
    ent_cols = [c for c in df_clean.columns if 'ENTIDAD' in str(c).upper()]
    mun_col = _get_mun_col(df_clean)
    act_cols = [c for c in df_clean.columns if 'ACTIVIDAD' in str(c).upper() or 'ECONÓMICA' in str(c).upper()]
    ue_cols = [c for c in df_clean.columns if 'UE' in str(c).upper() or 'UNIDADES' in str(c).upper()]
    pot_cols = [c for c in df_clean.columns if 'H001A' in str(c).upper() or 'PERSONAL' in str(c).upper()]
    
    if not act_cols or not ue_cols or not pot_cols:
        raise KeyError("Faltan columnas clave (Actividad, UE, o Personal).")
        
    y_col = year_cols[0] if year_cols else None
    e_col = ent_cols[0] if ent_cols else None
    m_col = mun_col
    a_col = act_cols[0]
    u_col = ue_cols[0]
    p_col = pot_cols[0]
    
    # Limpieza matemática
    for col in [u_col, p_col]:
        df_clean[col] = df_clean[col].astype(str).str.replace(',', '', regex=False).str.replace(r'\.0$', '', regex=True)
        df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0)
        
    results = []
    for _, row in df_clean.iterrows():
        # Filtro de año
        if target_year and y_col:
            y_val = str(row[y_col]).replace('.0', '').strip()
            if y_val != str(target_year): continue
                
        ent_val = str(row[e_col]).strip() if e_col else ""
        mun_val = str(row[m_col]).strip() if m_col else ""
        act_val = str(row[a_col]).strip()
        
        # Ignorar metadatos
        if 'NOTA:' in ent_val.upper() or 'NOTA:' in act_val.upper() or act_val.lower() in ['nan', '']:
            continue
            
        geo_code, geo_name = "", ""
        if mun_val and mun_val.lower() != 'nan':
            match_mun = re.match(r'^(\d{3})\s+(.*)$', mun_val)
            if match_mun: geo_code, geo_name = match_mun.group(1), match_mun.group(2)
            else: geo_name = mun_val
        else:
            match_ent = re.match(r'^(\d{2})\s+(.*)$', ent_val)
            if match_ent: geo_code, geo_name = match_ent.group(1), match_ent.group(2)
            else: geo_name = ent_val
                
        # Filtro de municipio seleccionado desde la interfaz
        if target_municipality:
            if not mun_val or mun_val.lower() == 'nan': continue
            if geo_code != target_municipality: continue
                
        # LIMPIEZA DE LA DESCRIPCIÓN Y REDUNDANCIAS (Aísla solo el texto posterior al número)
        match_act = re.match(r'^(Sector|Subsector|Rama|Subrama)?\s*(\d+[-\d]*)\s+(.*)', act_val, re.IGNORECASE)
        level, act_code, clean_act_text = "Total General", "", act_val
        
        if match_act:
            prefix = match_act.group(1)
            act_code = match_act.group(2)
            clean_act_text = match_act.group(3).strip() # Aislar descripción limpia
            
            if prefix: level = prefix.capitalize()
            else:
                code_len = len(act_code.replace('-', ''))
                if code_len <= 2: level = "Sector"
                elif code_len == 3: level = "Subsector"
                elif code_len == 4: level = "Rama"
                else: level = "Subrama"
        elif 'TOTAL MUNICIPAL' in act_val.upper():
            level = "Total Municipal"
            clean_act_text = "Total Municipal"
        elif 'TOTAL ESTATAL' in act_val.upper():
            level = "Total Estatal"
            clean_act_text = "Total Estatal"
            
        results.append({
            'Cód': geo_code,
            'Ubicación': geo_name,
            'Jerarquía': level,
            'Clave Econ.': act_code,
            'Actividad Económica': clean_act_text,
            'Unidades Econ.': row[u_col],
            'Personal Ocupado': row[p_col]
        })
        
    return pd.DataFrame(results)