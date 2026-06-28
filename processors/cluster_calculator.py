# processors/cluster_calculator.py
import pandas as pd

def calculate_clusters(df_econ, n_population):
    """
    Recibe la matriz económica ya filtrada por municipio y el Total de Población en Rango (N).
    Empareja en cascada Padre-Hijo, filtra inconsistencias y calcula Kc, Ks y Ki.
    """
    if df_econ is None or df_econ.empty:
        return pd.DataFrame()
        
    N = float(n_population) if n_population > 0 else 1.0
    
    data_dict = {}
    for _, row in df_econ.iterrows():
        code = str(row['Clave Econ.']).strip()
        if not code or code == 'nan': continue
        
        data_dict[code] = {
            'Nombre': str(row['Actividad Económica']).strip(),
            'UE': float(row['Unidades Econ.']),
            'PO': float(row['Personal Ocupado'])
        }
        
    available_codes = list(data_dict.keys())
    
    def find_parent(child_code):
        c = child_code.strip()
        if len(c) == 3:
            for p in available_codes:
                if '-' in p:
                    parts = p.split('-')
                    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                        if int(parts[0]) <= int(c[:2]) <= int(parts[1]): return p
                elif len(p) == 2 and c.startswith(p):
                    return p
        elif len(c) > 3:
            parent_guess = c[:-1]
            if parent_guess in available_codes:
                return parent_guess
        return None

    results = []
    
    for child_code, child_data in data_dict.items():
        parent_code = find_parent(child_code)
        
        if parent_code and parent_code in data_dict:
            parent_data = data_dict[parent_code]
            
            Ts = child_data['PO']
            Es = child_data['UE']
            Ti = parent_data['PO']
            Ei = parent_data['UE']
            
            # --- FILTRO ANTIFALSOS CLUSTERS ---
            # Si el INEGI censuró o reportó 0 en alguna métrica padre o hijo, el cálculo se contamina.
            if Ts == 0 or Ti == 0 or Es == 0 or Ei == 0:
                Kc, Ks, Ki = 0.0, 0.0, 0.0
                is_cluster = "Faltan Datos"
            else:
                Kc = ((Ts / Ti) / (Ti / N)) if (Ti > 0 and N > 0) else 0.0
                Ks = (Ts / Es) if Es > 0 else 0.0
                Ki = (Ti / Ei) if Ei > 0 else 0.0
                # Condición de validación de Cluster
                is_cluster = "Sí" if Ks > Ki else "No"
            
            results.append({
                'Cód. Ind (Padre)': parent_code,
                'Industria (Jerarquía Padre)': parent_data['Nombre'],
                'Cód. Sec (Hijo)': child_code,
                'Sector (Jerarquía Hija)': child_data['Nombre'],
                'Ts': Ts,
                'Ti': Ti,
                'Es': Es,
                'Ei': Ei,
                'Kc': Kc,
                'Ks': Ks,
                'Ki': Ki,
                '¿Es Cluster?': is_cluster
            })
            
    return pd.DataFrame(results)