# processors/cluster_calculator.py
import pandas as pd

def calculate_clusters(df_econ, n_population):
    """
    Recibe la matriz económica ya filtrada por municipio y el Total de Población en Rango (N).
    Empareja en cascada Padre-Hijo y calcula Kc, Ks y Ki para encontrar Clusters.
    """
    if df_econ is None or df_econ.empty:
        return pd.DataFrame()
        
    # Variables de control
    N = float(n_population) if n_population > 0 else 1.0  # Prevenir división por cero si no hay población
    
    # Extraer catálogo disponible en la matriz actual
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
        """Busca quién es la Industria Padre basándose en la longitud de la Clave Sectorial (Hijo)."""
        c = child_code.strip()
        if len(c) == 3:
            # Los hijos de 3 dígitos pertenecen a un padre de 2 dígitos o a un rango (ej. 31-33)
            for p in available_codes:
                if '-' in p:
                    parts = p.split('-')
                    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                        if int(parts[0]) <= int(c[:2]) <= int(parts[1]): return p
                elif len(p) == 2 and c.startswith(p):
                    return p
        elif len(c) > 3:
            # Para 4, 5 y 6 dígitos, el padre es simplemente la clave sin su último número
            parent_guess = c[:-1]
            if parent_guess in available_codes:
                return parent_guess
        return None

    results = []
    
    # Evaluar cada registro como posible "Sector (Hijo)"
    for child_code, child_data in data_dict.items():
        parent_code = find_parent(child_code)
        
        # Si tiene un Padre válido en los datos, hacemos la matemática
        if parent_code and parent_code in data_dict:
            parent_data = data_dict[parent_code]
            
            Ts = child_data['PO']
            Es = child_data['UE']
            Ti = parent_data['PO']
            Ei = parent_data['UE']
            
            # Cálculo de Coeficientes
            Kc = ((Ts / Ti) / (Ti / N)) if (Ti > 0 and N > 0) else 0.0
            Ks = (Ts / Es) if Es > 0 else 0.0
            Ki = (Ti / Ei) if Ei > 0 else 0.0
            
            # Condición de Cluster
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