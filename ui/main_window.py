# ui/main_window.py
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import re
from core.file_manager import load_inegi_data, open_file_in_system, extract_source_year
from processors.location_manager import clean_geographic_data, extract_states_dict, get_state_and_municipalities
from processors.working_age_calculator import calculate_population_differences
from processors.economic_calculator import analyze_economic_hierarchy, extract_economic_municipalities, extract_economic_years
from processors.cluster_calculator import calculate_clusters
from processors.population_interpolator import extrapolate_population_results, extrapolate_n_value

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1250x800")
        self.root.title("INEGI Data Processor - Análisis de Clusters y CAGR")
        
        self.dict_pop_raw = {}  
        self.dict_pop_clean = {} 
        self.economic_years = [] 
        
        self.df_econ_raw = None
        self.filepath_pop_last = ""
        self.filepath_econ = ""
        
        self.df_econ_cache = None 
        self.df_calc_cache = None 
        
        self.current_n_population = 0
        self.active_pop_year = "" # Rastrea exactamente qué año de población se está usando
        
        self.intersected_states = {}
        self.intersected_muns = {}
        
        self.pop_tab_built = False
        self.econ_tab_built = False
        self.calc_tab_built = False
        
        self.setup_ui()
        
    def setup_ui(self):
        # 1. CARGA DE ARCHIVOS
        top_frame = tk.LabelFrame(self.root, text=" 1. Carga de Matrices de Datos ", padx=5, pady=2)
        top_frame.pack(fill=tk.X, padx=10, pady=2)
        
        self.btn_load = tk.Button(top_frame, text="Añadir Archivo INEGI", command=self.load_smart_file, font=("Arial", 9, "bold"), bg="#e0e0e0")
        self.btn_load.grid(row=0, column=0, rowspan=2, padx=10, pady=5, sticky="ns")
        
        self.lbl_status_pop = tk.Label(top_frame, text="Población: ⚪ No cargado", fg="gray")
        self.lbl_status_pop.grid(row=0, column=1, sticky="w", padx=10, pady=1)
        self.btn_preview_pop = tk.Button(top_frame, text="👁 Último", state=tk.DISABLED, command=lambda: open_file_in_system(self.filepath_pop_last))
        self.btn_preview_pop.grid(row=0, column=2, padx=5, pady=1)
        
        self.lbl_status_econ = tk.Label(top_frame, text="Económico: ⚪ No cargado", fg="gray")
        self.lbl_status_econ.grid(row=1, column=1, sticky="w", padx=10, pady=1)
        self.btn_preview_econ = tk.Button(top_frame, text="👁 Ver", state=tk.DISABLED, command=lambda: open_file_in_system(self.filepath_econ))
        self.btn_preview_econ.grid(row=1, column=2, padx=5, pady=1)

        # 2. PREPARACIÓN DE ENTORNO
        prep_frame = tk.LabelFrame(self.root, text=" 2. Preparación de Entorno ", padx=5, pady=2)
        prep_frame.pack(fill=tk.X, padx=10, pady=2)
        
        self.chk_intersection_var = tk.BooleanVar(value=True)
        self.chk_intersection = tk.Checkbutton(prep_frame, text="Solo datos con intersección Estatal/Municipal", variable=self.chk_intersection_var, font=("Arial", 9, "bold"), fg="#b30000")
        self.chk_intersection.pack(side=tk.LEFT, padx=10, pady=5)
        
        self.btn_prepare = tk.Button(prep_frame, text="Preparar Entorno", command=self.prepare_environment, font=("Arial", 9, "bold"), bg="#2196F3", fg="white", state=tk.DISABLED)
        self.btn_prepare.pack(side=tk.LEFT, padx=20, pady=5)

        # 3. FILTRO MAESTRO (Geográfico)
        filter_frame = tk.LabelFrame(self.root, text=" 3. Filtro Geográfico Maestro ", padx=5, pady=2)
        filter_frame.pack(fill=tk.X, padx=10, pady=2)
        
        tk.Label(filter_frame, text="Estado:").pack(side=tk.LEFT, padx=5)
        self.cb_estado = ttk.Combobox(filter_frame, state="readonly", width=30)
        self.cb_estado.pack(side=tk.LEFT, padx=5)
        self.cb_estado.bind("<<ComboboxSelected>>", self.on_state_selected)
        
        tk.Label(filter_frame, text="Municipio:").pack(side=tk.LEFT, padx=15)
        self.cb_municipio = ttk.Combobox(filter_frame, state="readonly", width=30)
        self.cb_municipio.pack(side=tk.LEFT, padx=5)
        
        self.btn_process_all = tk.Button(filter_frame, text="Analizar y Construir", command=self.process_all_tabs, font=("Arial", 10, "bold"), bg="#4CAF50", fg="white", state=tk.DISABLED)
        self.btn_process_all.pack(side=tk.RIGHT, padx=10, pady=5)

        # 4. PESTAÑAS
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.tab_pop = tk.Frame(self.notebook, padx=10, pady=5)
        self.tab_econ = tk.Frame(self.notebook, padx=10, pady=5)
        self.tab_calc = tk.Frame(self.notebook, padx=10, pady=5)

    def load_smart_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Archivos INEGI", "*.csv *.xlsx *.xls")])
        if not filepath: return
        try:
            df_temp = load_inegi_data(filepath)
            cols_str = " ".join(list(df_temp.columns)).upper()
            name = filepath.split('/')[-1]
            
            if 'UE' in cols_str or 'H001A' in cols_str or 'ACTIVIDAD' in cols_str:
                self.filepath_econ = filepath
                self.df_econ_raw = df_temp
                self.lbl_status_econ.config(text=f"Económico: 🟢 {name}", fg="green")
                self.btn_preview_econ.config(state=tk.NORMAL)
                self.econ_tab_built = False
                self.calc_tab_built = False
            else:
                self.filepath_pop_last = filepath
                year_str = extract_source_year(filepath)
                year = int(year_str) if year_str.isdigit() else (2000 + len(self.dict_pop_raw))
                self.dict_pop_raw[year] = df_temp
                
                loaded_years = ", ".join([str(y) for y in sorted(self.dict_pop_raw.keys())])
                self.lbl_status_pop.config(text=f"Población: 🟢 Años cargados: [{loaded_years}]", fg="green")
                self.btn_preview_pop.config(state=tk.NORMAL)
                self.pop_tab_built = False
                self.calc_tab_built = False
                
            self.btn_prepare.config(state=tk.NORMAL)
            self.btn_process_all.config(state=tk.DISABLED)
        except Exception as e:
            messagebox.showerror("Error", f"Estructura incompatible:\n{str(e)}")

    def prepare_environment(self):
        self.intersected_states.clear()
        self.intersected_muns.clear()
        self.dict_pop_clean.clear()
        self.economic_years = []
        
        pop_states, pop_muns, econ_states, econ_muns = {}, {}, {}, {}
        
        for year, raw_df in self.dict_pop_raw.items():
            df_clean = clean_geographic_data(raw_df)
            clean_cols = {c: re.sub(r'^De\s+', '', str(c).strip(), flags=re.IGNORECASE) for c in df_clean.columns}
            df_clean.rename(columns=clean_cols, inplace=True)
            self.dict_pop_clean[year] = df_clean
        
        if self.dict_pop_clean:
            latest_year = max(self.dict_pop_clean.keys())
            latest_clean = self.dict_pop_clean[latest_year]
            
            pop_states = extract_states_dict(latest_clean)
            for _, r in latest_clean[latest_clean['Codigo'].str.len() == 5].iterrows():
                pop_muns[r['Codigo']] = str(r['Entidad_Municipio']).strip()
                
        if self.df_econ_raw is not None:
            econ_muns = extract_economic_municipalities(self.df_econ_raw)
            self.economic_years = extract_economic_years(self.df_econ_raw)
            ent_cols = [c for c in self.df_econ_raw.columns if 'ENTIDAD' in str(c).upper()]
            if ent_cols:
                for val in self.df_econ_raw[ent_cols[0]].dropna().unique():
                    match = re.match(r'^(\d{2})\s+(.*)$', str(val).strip())
                    if match and "NOTA" not in match.group(2).upper():
                        econ_states[match.group(1)] = match.group(2).strip()

        strict_mode = self.chk_intersection_var.get()
        if strict_mode and self.dict_pop_raw and self.df_econ_raw is not None:
            for code in pop_states:
                if code in econ_states:
                    mun_count = latest_clean[(latest_clean['Codigo'].str.len() == 5) & (latest_clean['Codigo'].str.startswith(code))].shape[0]
                    self.intersected_states[code] = f"🟢 {pop_states[code]}" if mun_count > 0 else f"⚪ {pop_states[code]}"
            for p_code, p_name in pop_muns.items():
                short_code = p_code[2:]
                if short_code in econ_muns and econ_muns[short_code].upper() in p_name.upper():
                    self.intersected_muns[p_code] = p_name
        else:
            base_states = pop_states if pop_states else {k: f"Entidad {k}" for k in econ_states}
            for code, name in base_states.items():
                m_count = latest_clean[(latest_clean['Codigo'].str.len() == 5) & (latest_clean['Codigo'].str.startswith(code))].shape[0] if self.dict_pop_raw else 1
                self.intersected_states[code] = f"🟢 {name}" if m_count > 0 else f"⚪ {name}"
                
            if pop_muns: self.intersected_muns = pop_muns
            elif econ_muns:
                st_code = list(econ_states.keys())[0] if len(econ_states) == 1 else "00"
                self.intersected_muns = {f"{st_code}{k}": v for k, v in econ_muns.items()}

        state_list = ["Toda la República Mexicana"] + [f"{k} - {v}" for k, v in self.intersected_states.items()]
        self.cb_estado['values'] = state_list
        if state_list:
            self.cb_estado.set(state_list[0])
            self.on_state_selected(None)
            
        if self.dict_pop_raw and not self.pop_tab_built:
            self.build_pop_tab()
            self.notebook.add(self.tab_pop, text="Análisis Demográfico")
            self.pop_tab_built = True
        if self.df_econ_raw is not None and not self.econ_tab_built:
            self.build_econ_tab()
            self.notebook.add(self.tab_econ, text="Censos Económicos")
            self.econ_tab_built = True
        if self.df_econ_raw is not None and not self.calc_tab_built:
            self.build_calc_tab()
            self.notebook.add(self.tab_calc, text="Cálculos (Clusters)")
            self.calc_tab_built = True
            
        self.btn_process_all.config(state=tk.NORMAL)
        messagebox.showinfo("Entorno Listo", "Entorno geográfico configurado. Proceda a Analizar.")

    def on_state_selected(self, event):
        state_sel = self.cb_estado.get()
        if "Toda la República" in state_sel:
            self.cb_municipio['values'] = ["N/A (Nivel Nacional)"]
            self.cb_municipio.set("N/A (Nivel Nacional)")
            self.cb_municipio.config(state=tk.DISABLED)
        else:
            self.cb_municipio.config(state="readonly")
            state_code = state_sel.replace("🟢 ", "").replace("⚪ ", "").split(" - ")[0]
            muns_list = [f"{k} - {v}" for k, v in self.intersected_muns.items() if k.startswith(state_code)]
            self.cb_municipio['values'] = ["Todos del Estado"] + muns_list
            self.cb_municipio.set("Todos del Estado")

    # ---------------------------------------------------------
    # CONSTRUCCIÓN DE INTERFACES Y SCROLL
    # ---------------------------------------------------------
    def configure_malla_scrolls(self, parent, tree):
        scy = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
        scy.grid(row=0, column=1, sticky="ns")
        scx = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=tree.xview)
        scx.grid(row=1, column=0, sticky="ew")
        tree.configure(yscroll=scy.set, xscroll=scx.set)

    def build_pop_tab(self):
        for w in self.tab_pop.winfo_children(): w.destroy()
        row1_frame = tk.Frame(self.tab_pop)
        row1_frame.pack(fill=tk.X, pady=(5, 5))
        
        tk.Label(row1_frame, text="Modo de Vista:").pack(side=tk.LEFT, padx=5)
        self.cb_view_mode = ttk.Combobox(row1_frame, state="readonly", width=30)
        
        modes = ["Extrapolación Compuesta (CAGR)"]
        if self.dict_pop_clean: modes += [f"Datos Reales ({y})" for y in sorted(list(self.dict_pop_clean.keys()))]
        self.cb_view_mode['values'] = modes
        self.cb_view_mode.set(modes[0])
        self.cb_view_mode.pack(side=tk.LEFT, padx=5)
        
        tk.Label(row1_frame, text="Año (Población):").pack(side=tk.LEFT, padx=15)
        self.cb_year_pop = ttk.Combobox(row1_frame, state="readonly", width=8)
        if self.economic_years:
            self.cb_year_pop['values'] = self.economic_years
            self.cb_year_pop.set(self.economic_years[0])
        elif self.dict_pop_clean:
            avail = sorted(list(self.dict_pop_clean.keys()))
            self.cb_year_pop['values'] = [str(y) for y in avail]
            self.cb_year_pop.set(str(avail[-1]))
        self.cb_year_pop.pack(side=tk.LEFT, padx=5)
        
        self.lbl_pop_nature = tk.Label(row1_frame, text="Estado: -", font=("Arial", 10, "bold"))
        self.lbl_pop_nature.pack(side=tk.RIGHT, padx=15)
        
        # Sincronización instantánea en cascada
        self.cb_view_mode.bind("<<ComboboxSelected>>", lambda e: self.process_population())
        self.cb_year_pop.bind("<<ComboboxSelected>>", lambda e: self.process_population())

        row2_frame = tk.Frame(self.tab_pop)
        row2_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(row2_frame, text="Filtro Edad:").pack(side=tk.LEFT, padx=5)
        self.cb_min_age = ttk.Combobox(row2_frame, state="readonly", width=12)
        self.cb_min_age.pack(side=tk.LEFT)
        tk.Label(row2_frame, text="a").pack(side=tk.LEFT)
        self.cb_max_age = ttk.Combobox(row2_frame, state="readonly", width=12)
        self.cb_max_age.pack(side=tk.LEFT)
        self.cb_min_age.bind("<<ComboboxSelected>>", lambda e: self.process_population())
        self.cb_max_age.bind("<<ComboboxSelected>>", lambda e: self.process_population())
        
        self.lbl_total_filtro = tk.Label(row2_frame, text="N (Población en rango): -", font=("Arial", 9, "bold"))
        self.lbl_total_filtro.pack(side=tk.RIGHT, padx=20)
        
        tree_frame = tk.Frame(self.tab_pop)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        self.tree_pop = ttk.Treeview(tree_frame)
        self.tree_pop.grid(row=0, column=0, sticky="nsew")
        self.configure_malla_scrolls(tree_frame, self.tree_pop)
        
        if self.dict_pop_clean:
            latest_clean = self.dict_pop_clean[max(self.dict_pop_clean.keys())]
            age_cols = [c for c in latest_clean.columns if re.search(r'años|\d+\s+a\s+\d+', str(c), re.IGNORECASE)]
            self.cb_min_age['values'], self.cb_max_age['values'] = age_cols, age_cols
            if age_cols:
                self.cb_min_age.set('15 a 19 años' if '15 a 19 años' in age_cols else age_cols[0])
                self.cb_max_age.set('60 a 64 años' if '60 a 64 años' in age_cols else age_cols[-1])

    def build_econ_tab(self):
        for w in self.tab_econ.winfo_children(): w.destroy()
        row1_frame = tk.Frame(self.tab_econ)
        row1_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(row1_frame, text="Año Censal Económico:").pack(side=tk.LEFT, padx=5)
        self.cb_year_econ = ttk.Combobox(row1_frame, state="readonly", width=8)
        self.cb_year_econ.pack(side=tk.LEFT, padx=5)
        # Aquí también enlazamos la sincronización en cascada
        self.cb_year_econ.bind("<<ComboboxSelected>>", lambda e: self.process_all_tabs())
        
        tk.Label(row1_frame, text="Buscar:").pack(side=tk.LEFT, padx=10)
        self.txt_act_code = tk.Entry(row1_frame, width=22)
        self.txt_act_code.pack(side=tk.LEFT, padx=5)
        self.txt_act_code.bind("<KeyRelease>", self.filter_economic_realtime)
        
        tk.Label(row1_frame, text="Filas:").pack(side=tk.LEFT, padx=5)
        self.cb_limit_econ = ttk.Combobox(row1_frame, state="readonly", width=8)
        self.cb_limit_econ['values'] = ["500", "1500", "5000", "Todos"]
        self.cb_limit_econ.set("1500")
        self.cb_limit_econ.pack(side=tk.LEFT, padx=5)
        self.cb_limit_econ.bind("<<ComboboxSelected>>", self.filter_economic_realtime)

        self.lbl_econ_count = tk.Label(row1_frame, text="Resultados: 0", font=("Arial", 9, "bold"), fg="#b30000")
        self.lbl_econ_count.pack(side=tk.RIGHT, padx=15)

        row2_frame = tk.Frame(self.tab_econ)
        row2_frame.pack(fill=tk.X, pady=(0, 5))

        tk.Label(row2_frame, text="Ordenar por:").pack(side=tk.LEFT, padx=5)
        self.cb_sort_col = ttk.Combobox(row2_frame, state="readonly", width=20)
        self.cb_sort_col['values'] = ["Jerarquía Original", "Unidades Econ.", "Personal Ocupado"]
        self.cb_sort_col.set("Jerarquía Original")
        self.cb_sort_col.pack(side=tk.LEFT, padx=5)
        self.cb_sort_col.bind("<<ComboboxSelected>>", self.filter_economic_realtime)

        self.cb_sort_order = ttk.Combobox(row2_frame, state="readonly", width=12)
        self.cb_sort_order['values'] = ["Descendente", "Ascendente"]
        self.cb_sort_order.set("Descendente")
        self.cb_sort_order.pack(side=tk.LEFT, padx=5)
        self.cb_sort_order.bind("<<ComboboxSelected>>", self.filter_economic_realtime)
        
        tree_frame = tk.Frame(self.tab_econ)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        self.tree_econ = ttk.Treeview(tree_frame)
        self.tree_econ.grid(row=0, column=0, sticky="nsew")
        self.configure_malla_scrolls(tree_frame, self.tree_econ)
        
        if self.economic_years:
            self.cb_year_econ['values'] = self.economic_years
            self.cb_year_econ.set(self.economic_years[0])

    def build_calc_tab(self):
        for w in self.tab_calc.winfo_children(): w.destroy()
        ctrl_frame = tk.Frame(self.tab_calc)
        ctrl_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(ctrl_frame, text="Buscar Industria/Sector:").pack(side=tk.LEFT, padx=5)
        self.txt_calc_search = tk.Entry(ctrl_frame, width=25)
        self.txt_calc_search.pack(side=tk.LEFT, padx=5)
        self.txt_calc_search.bind("<KeyRelease>", self.filter_calc_realtime)
        
        self.chk_clusters_only_var = tk.BooleanVar(value=False)
        self.chk_clusters_only = tk.Checkbutton(ctrl_frame, text="✅ Mostrar SOLAMENTE Clusters", variable=self.chk_clusters_only_var, font=("Arial", 9, "bold"), fg="green", command=self.filter_calc_realtime)
        self.chk_clusters_only.pack(side=tk.LEFT, padx=10)
        
        # Alerta visual dinámica
        self.lbl_calc_warning = tk.Label(ctrl_frame, text="", font=("Arial", 9, "bold"), fg="#e67e22")
        self.lbl_calc_warning.pack(side=tk.LEFT, padx=15)
        
        self.lbl_calc_count = tk.Label(ctrl_frame, text="Registros: 0", font=("Arial", 9, "bold"))
        self.lbl_calc_count.pack(side=tk.RIGHT, padx=15)
        
        tree_frame = tk.Frame(self.tab_calc)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        self.tree_calc = ttk.Treeview(tree_frame)
        self.tree_calc.grid(row=0, column=0, sticky="nsew")
        
        self.tree_calc.tag_configure('cluster_row', background='#d4edda')
        self.tree_calc.tag_configure('missing_data_row', background='#fff3cd')
        self.configure_malla_scrolls(tree_frame, self.tree_calc)

    # ---------------------------------------------------------
    # EXTRAPOLACIÓN, FILTRADO Y RENDERIZADO
    # ---------------------------------------------------------
    def process_all_tabs(self):
        self.current_n_population = 0
        if self.dict_pop_clean: self.process_population(auto_calc=False)
        if self.df_econ_raw is not None: 
            self.process_economic()
            self.process_calculations()

    def _get_single_year_population(self, year):
        df_clean = self.dict_pop_clean[year]
        state_sel, mun_sel = self.cb_estado.get(), self.cb_municipio.get()
        min_age, max_age = self.cb_min_age.get(), self.cb_max_age.get()
        cols = list(df_clean.columns)
        
        if min_age not in cols or max_age not in cols: return pd.DataFrame(), 0
            
        age_cols = cols[cols.index(min_age):cols.index(max_age)+1]
        
        if "Toda la República" in state_sel:
            valid_codes = list(self.intersected_states.keys())
            state_data = df_clean[df_clean['Codigo'].isin(valid_codes)]
            mun_data = df_clean[df_clean['Codigo'].str.len() == 5]
        else:
            state_code = state_sel.replace("🟢 ", "").replace("⚪ ", "").split(" - ")[0]
            state_data_all, mun_data_all = get_state_and_municipalities(df_clean, state_code)
            state_data = state_data_all
            if "Todos del Estado" in mun_sel: mun_data = mun_data_all
            else: mun_data = mun_data_all[mun_data_all['Codigo'] == mun_sel.split(" - ")[0]]
                
        if state_data.empty: return pd.DataFrame(), 0
        
        t_flt = sum(pd.to_numeric(str(x).replace(',', ''), errors='coerce') or 0 for col in age_cols for x in state_data[col].values)
        res_df = calculate_population_differences(state_data, mun_data, age_cols)
        return res_df, t_flt

    def process_population(self, auto_calc=True):
        try:
            target_year = self.cb_year_pop.get() 
            view_mode = self.cb_view_mode.get()
            available_years = sorted(list(self.dict_pop_clean.keys()))
            
            if not available_years: return
            
            if "Extrapolación" in view_mode and len(available_years) >= 2:
                self.active_pop_year = str(target_year)
                try: t_year_int = int(target_year)
                except ValueError: t_year_int = available_years[-1]
                    
                closest = sorted(available_years, key=lambda y: abs(y - t_year_int))
                y1, y2 = min(closest[0], closest[1]), max(closest[0], closest[1])
                
                df1, t_flt1 = self._get_single_year_population(y1)
                df2, t_flt2 = self._get_single_year_population(y2)
                
                if df1.empty or df2.empty: return
                
                t_flt_ex = extrapolate_n_value(t_flt1, t_flt2, y1, y2, target_year)
                self.current_n_population = t_flt_ex
                
                self.lbl_pop_nature.config(text=f"📈 SINTÉTICO: Extrapolado a {target_year} (mediante sucesión geométrica)", fg="#b30000")
                self.lbl_total_filtro.config(text=f"N Estimada ({target_year}): {t_flt_ex:,.0f}")
                
                final_df = extrapolate_population_results(df1, df2, y1, y2, target_year)
                self.render_tree(self.tree_pop, final_df, type_tab='pop')
            else:
                for yr in available_years:
                    if str(yr) in view_mode or len(available_years) == 1:
                        self.active_pop_year = str(yr)
                        df_real, t_real = self._get_single_year_population(yr)
                        self.current_n_population = t_real
                        
                        self.lbl_pop_nature.config(text=f"🟢 DATOS REALES: Censo Original {yr}", fg="green")
                        self.lbl_total_filtro.config(text=f"N Real ({yr}): {t_real:,.0f}")
                        self.render_tree(self.tree_pop, df_real, type_tab='pop')
                        break
                        
            # Si el usuario manipuló un control de población, auto-sincronizamos los Clusters
            if auto_calc and self.df_econ_raw is not None and self.calc_tab_built:
                self.process_calculations()
                
        except Exception as e:
            messagebox.showerror("Error Población", str(e))

    def process_economic(self):
        try:
            state_sel, mun_sel, target_year = self.cb_estado.get(), self.cb_municipio.get(), self.cb_year_econ.get()
            self.txt_act_code.delete(0, tk.END)
            
            df_full = analyze_economic_hierarchy(self.df_econ_raw, None, target_year)
            if df_full.empty:
                self.df_econ_cache = df_full
                self.filter_economic_realtime(None)
                return

            if "Toda la República" in state_sel:
                self.df_econ_cache = df_full
            else:
                state_name = state_sel.replace("🟢 ", "").replace("⚪ ", "").split(" - ")[1].strip().upper()
                state_code = state_sel.replace("🟢 ", "").replace("⚪ ", "").split(" - ")[0]
                
                if "Todos del Estado" in mun_sel:
                    valid_mun_names = [v.upper() for k, v in self.intersected_muns.items() if k.startswith(state_code)]
                    valid_mun_names.append(state_name)
                    if len(valid_mun_names) <= 1: valid_mun_names = df_full['Ubicación'].str.upper().unique().tolist()
                    self.df_econ_cache = df_full[df_full['Ubicación'].str.upper().isin(valid_mun_names)]
                else:
                    mun_name = mun_sel.split(" - ")[1].strip().upper()
                    self.df_econ_cache = df_full[df_full['Ubicación'].str.upper().isin([mun_name, state_name])]
                    
            self.filter_economic_realtime(None)
        except Exception as e:
            messagebox.showerror("Error Económico", str(e))

    def process_calculations(self):
        try:
            if hasattr(self, 'txt_calc_search'): self.txt_calc_search.delete(0, tk.END)
            
            # --- EVALUACIÓN DE LA LEYENDA (Toma ambos datos de los desplegables) ---
            pop_year = getattr(self, 'active_pop_year', "")
            econ_year = self.cb_year_econ.get() if hasattr(self, 'cb_year_econ') and self.cb_year_econ.winfo_exists() else ""
            
            if pop_year and econ_year and pop_year != econ_year:
                if hasattr(self, 'lbl_calc_warning'):
                    self.lbl_calc_warning.config(text=f"⚠️ Advertencia: Población ({pop_year}) vs Economía ({econ_year}). Imprecisión temporal.")
            else:
                if hasattr(self, 'lbl_calc_warning'):
                    self.lbl_calc_warning.config(text="")
            
            # Usar la N que extrajo exactamente del filtro de Población actual
            n_final_cluster = self.current_n_population if self.current_n_population > 0 else 1.0
            
            self.df_calc_cache = calculate_clusters(self.df_econ_cache, n_final_cluster)
            self.filter_calc_realtime()
            
        except Exception as e:
            messagebox.showerror("Error en Cálculos", f"Fallo en matemática de clusters:\n{str(e)}")

    def filter_economic_realtime(self, event=None):
        if self.df_econ_cache is None or self.df_econ_cache.empty: return
        search = self.txt_act_code.get().strip().lower()
        filtered = self.df_econ_cache.copy()
        
        if search != "":
            filtered = filtered[
                filtered['Clave Econ.'].astype(str).str.startswith(search) | 
                filtered['Actividad Económica'].astype(str).str.lower().str.contains(search, regex=False, na=False)
            ]

        if hasattr(self, 'cb_sort_col') and self.cb_sort_col.winfo_exists():
            sort_val = self.cb_sort_col.get()
            if sort_val != "Jerarquía Original":
                col = {"Unidades Econ.": "Unidades Econ.", "Personal Ocupado": "Personal Ocupado"}.get(sort_val)
                if col: filtered = filtered.sort_values(by=col, ascending=(self.cb_sort_order.get() == "Ascendente"))

        self.render_tree(self.tree_econ, filtered, type_tab='econ')

    def filter_calc_realtime(self, event=None):
        if self.df_calc_cache is None or self.df_calc_cache.empty: return
        search = self.txt_calc_search.get().strip().lower()
        filtered = self.df_calc_cache.copy()
        
        if search != "":
            filtered = filtered[
                filtered['Cód. Sec (Hijo)'].astype(str).str.startswith(search) | 
                filtered['Sector (Jerarquía Hija)'].astype(str).str.lower().str.contains(search, regex=False, na=False) |
                filtered['Industria (Jerarquía Padre)'].astype(str).str.lower().str.contains(search, regex=False, na=False)
            ]
            
        if self.chk_clusters_only_var.get():
            filtered = filtered[filtered['¿Es Cluster?'] == "Sí"]
            
        self.lbl_calc_count.config(text=f"Registros: {len(filtered):,.0f}")
        self.render_tree(self.tree_calc, filtered, type_tab='calc')

    def render_tree(self, tree, df, type_tab='pop'):
        tree.delete(*tree.get_children())
        if df.empty: return
        
        display_df = df
        if type_tab == 'econ' and hasattr(self, 'cb_limit_econ'):
            limite = self.cb_limit_econ.get()
            if limite != "Todos": display_df = df.head(int(limite))
            self.lbl_econ_count.config(text=f"Resultados: {len(df):,.0f} (Mostrando {len(display_df):,.0f})")
            
        tree["columns"] = list(display_df.columns)
        tree["show"] = "headings"
        
        for col in display_df.columns:
            if type_tab == 'calc':
                if 'Cód' in col: w, align = 60, 'center'
                elif 'Industria' in col or 'Sector' in col: w, align = 200, 'w'
                elif col in ['Ts', 'Ti', 'Es', 'Ei']: w, align = 60, 'center'
                elif col in ['Kc', 'Ks', 'Ki']: w, align = 80, 'center'
                else: w, align = 90, 'center'
            else:
                max_len = max([len(str(col))] + [len(f"{x:,.0f}" if isinstance(x, (int, float)) else str(x)) for x in display_df[col]])
                align = "w" if col == 'Actividad Económica' else "center"
                if type_tab == 'pop': w = (max_len * 9) + 15 if col == 'Municipio' else (max_len * 8) + 10
                else: w = min(int((max_len * 6) + 4), 250) if col == 'Actividad Económica' else (max_len * 7.5) + 6
                
            tree.heading(col, text=col)
            tree.column(col, width=int(w), minwidth=int(w), stretch=tk.NO, anchor=align)
            
        for _, row in display_df.iterrows():
            vals = []
            is_cluster = False
            is_missing = False
            
            for col, item in zip(display_df.columns, list(row)):
                if col == '¿Es Cluster?':
                    if item == 'Sí': is_cluster = True
                    elif item == 'Faltan Datos': is_missing = True
                    
                if type_tab == 'calc' and col in ['Kc', 'Ks', 'Ki']: vals.append(f"{item:,.3f}")
                elif isinstance(item, float): vals.append(f"{item:,.0f}")
                else: vals.append(str(item))
                    
            tags = ()
            if is_cluster: tags = ('cluster_row',)
            elif is_missing: tags = ('missing_data_row',)
                
            tree.insert("", "end", values=vals, tags=tags)