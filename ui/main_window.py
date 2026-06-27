# ui/main_window.py
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import re
from core.file_manager import load_inegi_data, open_file_in_system, extract_source_year
from processors.location_manager import clean_geographic_data, extract_states_dict, get_state_and_municipalities
from processors.working_age_calculator import calculate_population_differences
from processors.economic_calculator import analyze_economic_hierarchy, extract_economic_municipalities, extract_economic_years

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1200x780")
        self.root.title("INEGI Data Processor - Optimizado")
        
        # Matrices en bruto en memoria
        self.df_pop_raw = None
        self.df_econ_raw = None
        self.filepath_pop = ""
        self.filepath_econ = ""
        
        # Cachés de procesamiento
        self.df_clean_pop = None
        self.df_econ_cache = None 
        
        # Catálogos de filtrado intersecado
        self.intersected_states = {}
        self.intersected_muns = {}
        
        self.pop_tab_built = False
        self.econ_tab_built = False
        
        self.setup_ui()
        
    def setup_ui(self):
        # ==========================================
        # PANEL 1: PANEL MAESTRO DE CARGA
        # ==========================================
        top_frame = tk.LabelFrame(self.root, text=" 1. Carga de Matrices de Datos ", padx=10, pady=5)
        top_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.btn_load = tk.Button(top_frame, text="Cargar Archivo INEGI", command=self.load_smart_file, font=("Arial", 9, "bold"), bg="#e0e0e0")
        self.btn_load.grid(row=0, column=0, rowspan=2, padx=10, pady=5, sticky="ns")
        
        self.lbl_status_pop = tk.Label(top_frame, text="Población: ⚪ No cargado", fg="gray")
        self.lbl_status_pop.grid(row=0, column=1, sticky="w", padx=10, pady=2)
        
        self.lbl_status_econ = tk.Label(top_frame, text="Económico: ⚪ No cargado", fg="gray")
        self.lbl_status_econ.grid(row=1, column=1, sticky="w", padx=10, pady=2)

        # ==========================================
        # PANEL 2: FILTROS Y CONTROL DE ETAPAS
        # ==========================================
        ctrl_frame = tk.LabelFrame(self.root, text=" 2. Configuración de Entorno y Filtro Maestro ", padx=10, pady=5)
        ctrl_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Casilla de optimización de intersección
        self.chk_intersection_var = tk.BooleanVar(value=True)
        self.chk_intersection = tk.Checkbutton(ctrl_frame, text="Solo cargar datos con intersección Estatal/Municipal", variable=self.chk_intersection_var, font=("Arial", 9, "bold"), fg="#b30000")
        self.chk_intersection.grid(row=0, column=0, columnspan=2, sticky="w", pady=2, padx=5)
        
        # ETAPA 1: Inicializador de entorno
        self.btn_prepare = tk.Button(ctrl_frame, text="Preparar Entorno", command=self.prepare_environment, font=("Arial", 9, "bold"), bg="#2196F3", fg="white", state=tk.DISABLED)
        self.btn_prepare.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        
        # Filtros de Cobertura Geográfica Sincronizados
        geo_frame = tk.Frame(ctrl_frame)
        geo_frame.grid(row=1, column=1, padx=15, pady=5, sticky="w")
        
        self.geo_level_var = tk.StringVar(value="Estado")
        tk.Radiobutton(geo_frame, text="Nivel Nacional", variable=self.geo_level_var, value="Nacional", command=self.update_global_locations).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(geo_frame, text="Estado", variable=self.geo_level_var, value="Estado", command=self.update_global_locations).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(geo_frame, text="Municipio", variable=self.geo_level_var, value="Municipio", command=self.update_global_locations).pack(side=tk.LEFT, padx=5)
        
        tk.Label(geo_frame, text="Selección Global:").pack(side=tk.LEFT, padx=5)
        self.cb_global_loc = ttk.Combobox(geo_frame, state="readonly", width=38)
        self.cb_global_loc.pack(side=tk.LEFT, padx=5)
        
        # ETAPA 2: Procesador y Renderizador Final
        self.btn_process_all = tk.Button(ctrl_frame, text="Filtrar y Dibujar Tablas", command=self.process_all_tabs, font=("Arial", 10, "bold"), bg="#4CAF50", fg="white", state=tk.DISABLED)
        self.btn_process_all.grid(row=1, column=2, padx=30, pady=5, sticky="e")

        # ==========================================
        # PANEL 3: NÚCLEO DE PESTAÑAS EXPANSIVAS (Frontal Maximizado)
        # ==========================================
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.tab_pop = tk.Frame(self.notebook, padx=10, pady=10)
        self.tab_econ = tk.Frame(self.notebook, padx=10, pady=10)

    # ---------------------------------------------------------
    # GESTIÓN DE CARGA INTELIGENTE
    # ---------------------------------------------------------
    def load_smart_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Archivos de Datos INEGI", "*.csv *.xlsx *.xls")])
        if not filepath: return
        try:
            df_temp = load_inegi_data(filepath)
            cols_str = " ".join(list(df_temp.columns)).upper()
            name = filepath.split('/')[-1]
            
            if 'UE' in cols_str or 'H001A' in cols_str or 'ACTIVIDAD' in cols_str:
                self.filepath_econ = filepath
                self.df_econ_raw = df_temp
                self.lbl_status_econ.config(text=f"Económico: 🟢 {name}", fg="green")
                self.econ_tab_built = False 
            else:
                self.filepath_pop = filepath
                self.df_pop_raw = df_temp
                self.lbl_status_pop.config(text=f"Población: 🟢 {name}", fg="green")
                self.pop_tab_built = False
                
            self.btn_prepare.config(state=tk.NORMAL)
            self.btn_process_all.config(state=tk.DISABLED)
        except Exception as e:
            messagebox.showerror("Error de Carga", f"Estructura incompatible:\n{str(e)}")

    # ---------------------------------------------------------
    # ETAPA 1: PROCESAMIENTO GEOGRÁFICO DE INTERSECCIÓN
    # ---------------------------------------------------------
    def prepare_environment(self):
        """Cruza los datos de población y economía para hallar zonas coincidentes."""
        self.intersected_states.clear()
        self.intersected_muns.clear()
        
        pop_states, pop_muns = {}, {}
        econ_states, econ_muns = {}, {}
        
        # 1. Extraer universo de población
        if self.df_pop_raw is not None:
            self.df_clean_pop = clean_geographic_data(self.df_pop_raw)
            clean_cols = {c: re.sub(r'^De\s+', '', str(c).strip(), flags=re.IGNORECASE) for c in self.df_clean_pop.columns}
            self.df_clean_pop.rename(columns=clean_cols, inplace=True)
            
            pop_states = extract_states_dict(self.df_clean_pop)
            for _, r in self.df_clean_pop[self.df_clean_pop['Codigo'].str.len() == 5].iterrows():
                pop_muns[r['Codigo']] = str(r['Entidad_Municipio']).strip()
                
        # 2. Extraer universo económico
        if self.df_econ_raw is not None:
            econ_muns = extract_economic_municipalities(self.df_econ_raw)
            ent_cols = [c for c in self.df_econ_raw.columns if 'ENTIDAD' in str(c).upper()]
            if ent_cols:
                for val in self.df_econ_raw[ent_cols[0]].dropna().unique():
                    match = re.match(r'^(\d{2})\s+(.*)$', str(val).strip())
                    if match and "NOTA" not in match.group(2).upper():
                        econ_states[match.group(1)] = match.group(2).strip()

        # 3. EJECUTAR FILTRO DE INTERSECCIÓN U OPTIMIZACIÓN REGIONAL
        strict_mode = self.chk_intersection_var.get()
        
        if strict_mode and self.df_pop_raw is not None and self.df_econ_raw is not None:
            # Cruzar Estados
            for code in pop_states:
                if code in econ_states:
                    # Contar si posee desgloses válidos
                    mun_count = self.df_clean_pop[(self.df_clean_pop['Codigo'].str.len() == 5) & (self.df_clean_pop['Codigo'].str.startswith(code))].shape[0]
                    self.intersected_states[code] = f"🟢 {pop_states[code]}" if mun_count > 0 else f"⚪ {pop_states[code]}"
            # Cruzar Municipios (Vincular claves cortas del censo con claves de 5 dígitos de población)
            for p_code, p_name in pop_muns.items():
                short_code = p_code[2:] # ej '14001' -> '001'
                if short_code in econ_muns and econ_muns[short_code].upper() in p_name.upper():
                    self.intersected_muns[p_code] = p_name
        else:
            # Modo libre: combina la información disponible
            base_states = pop_states if pop_states else {k: f"Entidad {k}" for k in econ_states}
            for code, name in base_states.items():
                m_count = self.df_clean_pop[(self.df_clean_pop['Codigo'].str.len() == 5) & (self.df_clean_pop['Codigo'].str.startswith(code))].shape[0] if self.df_pop_raw is not None else 1
                self.intersected_states[code] = f"🟢 {name}" if m_count > 0 else f"⚪ {name}"
                
            self.intersected_muns = pop_muns if pop_muns else {f"00{k}": v for k, v in econ_muns.items()}

        self.update_global_locations()
        
        # Levantar contenedores limpios en las pestañas (sin pintar registros aún)
        if self.df_pop_raw is not None and not self.pop_tab_built:
            self.build_pop_tab()
            self.notebook.add(self.tab_pop, text="Análisis Demográfico")
            self.pop_tab_built = True
            
        if self.df_econ_raw is not None and not self.econ_tab_built:
            self.build_econ_tab()
            self.notebook.add(self.tab_econ, text="Censos Económicos")
            self.econ_tab_built = True
            
        self.btn_process_all.config(state=tk.NORMAL)
        messagebox.showinfo("Etapa 1 Completada", "Entorno geográfico estructurado en memoria RAM.\nSeleccione el filtro geográfico y proceda a filtrar.")

    def update_global_locations(self):
        lvl = self.geo_level_var.get()
        if lvl == "Nacional":
            self.cb_global_loc['values'] = ["00 - Áreas Geográficas con Intersección Activa"]
        elif lvl == "Estado":
            self.cb_global_loc['values'] = [f"{k} - {v}" for k, v in self.intersected_states.items()]
        elif lvl == "Municipio":
            self.cb_global_loc['values'] = [f"{k} - {v}" for k, v in self.intersected_muns.items()]
            
        if self.cb_global_loc['values']:
            self.cb_global_loc.set(self.cb_global_loc['values'][0])

    # ---------------------------------------------------------
    # CONSTRUCCIÓN VISUAL DE FILTROS INTERNOS
    # ---------------------------------------------------------
    def build_pop_tab(self):
        for w in self.tab_pop.winfo_children(): w.destroy()
        
        filter_frame = tk.Frame(self.tab_pop)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        detected_year = extract_source_year(self.filepath_pop)
        tk.Label(filter_frame, text=f"Año Matriz: {detected_year}", font=("Arial", 9, "bold"), fg="blue").pack(side=tk.LEFT, padx=10)
        
        tk.Label(filter_frame, text="Filtro Rango de Edad:").pack(side=tk.LEFT, padx=15)
        self.cb_min_age = ttk.Combobox(filter_frame, state="readonly", width=12)
        self.cb_min_age.pack(side=tk.LEFT, padx=2)
        tk.Label(filter_frame, text="a").pack(side=tk.LEFT)
        self.cb_max_age = ttk.Combobox(filter_frame, state="readonly", width=12)
        self.cb_max_age.pack(side=tk.LEFT, padx=2)
        
        summary_frame = tk.Frame(self.tab_pop)
        summary_frame.pack(fill=tk.X, pady=(0, 10))
        self.lbl_total_entidad = tk.Label(summary_frame, text="Población base (Padre): -", font=("Arial", 9, "bold"))
        self.lbl_total_entidad.pack(side=tk.LEFT, padx=10)
        self.lbl_total_filtro = tk.Label(summary_frame, text="Población en rango: -", font=("Arial", 9, "bold"))
        self.lbl_total_filtro.pack(side=tk.LEFT, padx=20)
        
        tree_frame = tk.Frame(self.tab_pop)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        
        self.tree_pop = ttk.Treeview(tree_frame)
        self.tree_pop.grid(row=0, column=0, sticky="nsew")
        self.configure_malla_scrolls(tree_frame, self.tree_pop)
        
        age_cols = [c for c in self.df_clean_pop.columns if re.search(r'años|\d+\s+a\s+\d+', str(c), re.IGNORECASE)]
        self.cb_min_age['values'] = age_cols
        self.cb_max_age['values'] = age_cols
        if '15 a 19 años' in age_cols: self.cb_min_age.set('15 a 19 años')
        elif age_cols: self.cb_min_age.set(age_cols[0])
        if '60 a 64 años' in age_cols: self.cb_max_age.set('60 a 64 años')
        elif age_cols: self.cb_max_age.set(age_cols[-1])

    def build_econ_tab(self):
        for w in self.tab_econ.winfo_children(): w.destroy()
        
        filter_frame = tk.Frame(self.tab_econ)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(filter_frame, text="Año Censal:").pack(side=tk.LEFT, padx=5)
        self.cb_year_econ = ttk.Combobox(filter_frame, state="readonly", width=8)
        self.cb_year_econ.pack(side=tk.LEFT, padx=5)
        
        tk.Label(filter_frame, text="Buscar actividad económica:").pack(side=tk.LEFT, padx=25)
        self.txt_act_code = tk.Entry(filter_frame, width=22)
        self.txt_act_code.pack(side=tk.LEFT, padx=5)
        self.txt_act_code.bind("<KeyRelease>", self.filter_economic_realtime)
        
        tree_frame = tk.Frame(self.tab_econ)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        
        self.tree_econ = ttk.Treeview(tree_frame)
        self.tree_econ.grid(row=0, column=0, sticky="nsew")
        self.configure_malla_scrolls(tree_frame, self.tree_econ)
        
        years = extract_economic_years(self.df_econ_raw)
        if years:
            self.cb_year_econ['values'] = years
            self.cb_year_econ.set(years[0])

    def configure_malla_scrolls(self, parent, tree):
        scy = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
        scy.grid(row=0, column=1, sticky="ns")
        scx = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=tree.xview)
        scx.grid(row=1, column=0, sticky="ew")
        tree.configure(yscroll=scy.set, xscroll=scx.set)

    # ---------------------------------------------------------
    # ETAPA 2: FLUJO DE PROCESAMIENTO Y DIBUJADO DE MATRICES
    # ---------------------------------------------------------
    def process_all_tabs(self):
        """Dispara de manera sincronizada la filtración y pintado de ambas tablas."""
        if self.df_pop_raw is not None: self.process_population()
        if self.df_econ_raw is not None: self.process_economic()

    def process_population(self):
        try:
            lvl = self.geo_level_var.get()
            sel = self.cb_global_loc.get()
            if not sel: return
            
            geo_code = sel.replace("🟢 ", "").replace("⚪ ", "").split(" - ")[0]
            
            # Segmentación de matriz demográfica según nivel del Filtro Maestro
            if lvl == "Estado":
                state_data, mun_data = get_state_and_municipalities(self.df_clean_pop, geo_code)
            elif lvl == "Municipio":
                st_code = geo_code[:2]
                state_data, mun_all = get_state_and_municipalities(self.df_clean_pop, st_code)
                mun_data = mun_all[mun_all['Codigo'] == geo_code]
            else: # Nivel Nacional (Compila todos los estados de la intersección)
                valid_codes = list(self.intersected_states.keys())
                state_data = self.df_clean_pop[self.df_clean_pop['Codigo'].isin(valid_codes)]
                mun_data = self.df_clean_pop[self.df_clean_pop['Codigo'].str.len() == 5]
                
            if state_data.empty: return
            
            min_age, max_age = self.cb_min_age.get(), self.cb_max_age.get()
            cols = list(self.df_clean_pop.columns)
            age_cols = cols[cols.index(min_age):cols.index(max_age)+1]
            
            # Limpieza y renderizado de indicadores resumen
            t_ent = sum(pd.to_numeric(str(x).replace(',', ''), errors='coerce') or 0 for x in state_data['Total'].values)
            t_flt = 0
            for col in age_cols:
                t_flt += sum(pd.to_numeric(str(x).replace(',', ''), errors='coerce') or 0 for x in state_data[col].values)
                
            self.lbl_total_entidad.config(text=f"Población base (Padre): {t_ent:,.0f}")
            self.lbl_total_filtro.config(text=f"Población en rango: {t_flt:,.0f}")
            
            res_df = calculate_population_differences(state_data, mun_data, age_cols)
            self.render_tree(self.tree_pop, res_df, is_pop=True)
        except Exception as e:
            print(f"Desfase en Demografía: {e}")

    def process_economic(self):
        try:
            lvl = self.geo_level_var.get()
            sel = self.cb_global_loc.get()
            if not sel: return
            
            target_mun = None
            if lvl == "Municipio":
                geo_name = sel.split(" - ")[1].upper()
                econ_muns = extract_economic_municipalities(self.df_econ_raw)
                for k, v in econ_muns.items():
                    if v.upper() == geo_name:
                        target_mun = k
                        break
            elif lvl == "Estado":
                # Si es un estado, podemos forzar a que filtre las actividades de los municipios de este estado
                pass
                
            target_year = self.cb_year_econ.get()
            self.txt_act_code.delete(0, tk.END)
            
            self.df_econ_cache = analyze_economic_hierarchy(self.df_econ_raw, target_mun, target_year)
            
            # Filtro acumulativo secundario si seleccionó un estado en cobertura nacional
            if lvl == "Estado" and not self.df_econ_cache.empty and 'Cód' in self.df_econ_cache.columns:
                st_code = sel.replace("🟢 ", "").replace("⚪ ", "").split(" - ")[0]
                # En censo económico, el municipio inicia con la clave del estado o se vincula por nombre
                pass
                
            self.render_tree(self.tree_econ, self.df_econ_cache, is_pop=False)
        except Exception as e:
            print(f"Desfase Económico: {e}")

    def filter_economic_realtime(self, event):
        if self.df_econ_cache is None or self.df_econ_cache.empty: return
        search = self.txt_act_code.get().strip().lower()
        if search == "":
            self.render_tree(self.tree_econ, self.df_econ_cache, is_pop=False)
        else:
            filtered = self.df_econ_cache[
                self.df_econ_cache['Clave Econ.'].astype(str).str.startswith(search) | 
                self.df_econ_cache['Actividad Económica'].astype(str).str.lower().str.contains(search, regex=False, na=False)
            ]
            self.render_tree(self.tree_econ, filtered, is_pop=False)

    # ---------------------------------------------------------
    # RENDERIZADOR DE ALINEACIÓN Y ANCHO ESTRECHO CEÑIDO
    # ---------------------------------------------------------
    def render_tree(self, tree, df, is_pop):
        tree.delete(*tree.get_children())
        if df.empty: return
        
        tree["columns"] = list(df.columns)
        tree["show"] = "headings"
        
        for col in df.columns:
            max_len = len(str(col))
            for item in df[col]:
                item_str = f"{item:,.0f}" if isinstance(item, (int, float)) else str(item)
                if len(item_str) > max_len: max_len = len(item_str)
            
            # Alinear descripciones a la izquierda, claves y totales al centro
            align = "w" if col == 'Actividad Económica' else "center"
            
            if is_pop:
                w = (max_len * 8) + 12 if col == 'Municipio' else ((max_len * 9) + 10 if col == 'Cód. Mpio' else ((max_len * 7) + 4 if " a " in str(col) or "años" in str(col).lower() else (max_len * 7.5) + 6))
            else:
                # ESTRANGULACIÓN DE ANCHO: Forzar a que la actividad económica no sature el frontal (Máx 250px)
                if col == 'Actividad Económica':
                    w = min(int((max_len * 6) + 4), 250)
                else:
                    w = (max_len * 8) + 8 if 'Ubicación' in str(col) or 'Municipio' in str(col) else (max_len * 7.5) + 4
                
            tree.heading(col, text=col)
            tree.column(col, width=int(w), minwidth=int(w), stretch=tk.NO, anchor=align)
            
        for _, row in df.iterrows():
            vals = [f"{item:,.0f}" if isinstance(item, (int, float)) else item for item in list(row)]
            tree.insert("", "end", values=vals)