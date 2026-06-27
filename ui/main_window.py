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
        self.root.title("INEGI Data Processor | Cluster Finder")
        
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
        # PASO 1: CARGA DE ARCHIVOS Y PREVISUALIZACIÓN
        # ==========================================
        top_frame = tk.LabelFrame(self.root, text=" 1. Carga de Matrices de Datos ", padx=5, pady=2)
        top_frame.pack(fill=tk.X, padx=10, pady=2)
        
        self.btn_load = tk.Button(top_frame, text="Cargar Archivo INEGI", command=self.load_smart_file, font=("Arial", 9, "bold"), bg="#e0e0e0")
        self.btn_load.grid(row=0, column=0, rowspan=2, padx=10, pady=5, sticky="ns")
        
        self.lbl_status_pop = tk.Label(top_frame, text="Población: ⚪ No cargado", fg="gray")
        self.lbl_status_pop.grid(row=0, column=1, sticky="w", padx=10, pady=1)
        self.btn_preview_pop = tk.Button(top_frame, text="👁 Ver Archivo", state=tk.DISABLED, command=lambda: open_file_in_system(self.filepath_pop))
        self.btn_preview_pop.grid(row=0, column=2, padx=5, pady=1)
        
        self.lbl_status_econ = tk.Label(top_frame, text="Económico: ⚪ No cargado", fg="gray")
        self.lbl_status_econ.grid(row=1, column=1, sticky="w", padx=10, pady=1)
        self.btn_preview_econ = tk.Button(top_frame, text="👁 Ver Archivo", state=tk.DISABLED, command=lambda: open_file_in_system(self.filepath_econ))
        self.btn_preview_econ.grid(row=1, column=2, padx=5, pady=1)

        # ==========================================
        # PASO 2: PREPARACIÓN DE ENTORNO
        # ==========================================
        prep_frame = tk.LabelFrame(self.root, text=" 2. Preparación de Entorno ", padx=5, pady=2)
        prep_frame.pack(fill=tk.X, padx=10, pady=2)
        
        self.chk_intersection_var = tk.BooleanVar(value=True)
        self.chk_intersection = tk.Checkbutton(prep_frame, text="Solo cargar datos con intersección Estatal/Municipal", variable=self.chk_intersection_var, font=("Arial", 9, "bold"), fg="#b30000")
        self.chk_intersection.pack(side=tk.LEFT, padx=10, pady=5)
        
        self.btn_prepare = tk.Button(prep_frame, text="Preparar Entorno", command=self.prepare_environment, font=("Arial", 9, "bold"), bg="#2196F3", fg="white", state=tk.DISABLED)
        self.btn_prepare.pack(side=tk.LEFT, padx=20, pady=5)

        # ==========================================
        # PASO 3: FILTRO GEOGRÁFICO Y ANÁLISIS
        # ==========================================
        filter_frame = tk.LabelFrame(self.root, text=" 3. Filtro Geográfico Maestro y Análisis ", padx=5, pady=2)
        filter_frame.pack(fill=tk.X, padx=10, pady=2)
        
        tk.Label(filter_frame, text="Estado:").pack(side=tk.LEFT, padx=5)
        self.cb_estado = ttk.Combobox(filter_frame, state="readonly", width=35)
        self.cb_estado.pack(side=tk.LEFT, padx=5)
        self.cb_estado.bind("<<ComboboxSelected>>", self.on_state_selected)
        
        tk.Label(filter_frame, text="Municipio:").pack(side=tk.LEFT, padx=15)
        self.cb_municipio = ttk.Combobox(filter_frame, state="readonly", width=35)
        self.cb_municipio.pack(side=tk.LEFT, padx=5)
        
        self.btn_process_all = tk.Button(filter_frame, text="Analizar y Dibujar Tablas", command=self.process_all_tabs, font=("Arial", 10, "bold"), bg="#4CAF50", fg="white", state=tk.DISABLED)
        self.btn_process_all.pack(side=tk.RIGHT, padx=10, pady=5)

        # ==========================================
        # PANEL DE PESTAÑAS Y TABLAS (MAXIMIZADO)
        # ==========================================
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.tab_pop = tk.Frame(self.notebook, padx=10, pady=5)
        self.tab_econ = tk.Frame(self.notebook, padx=10, pady=5)

    # ---------------------------------------------------------
    # PASO 1: CARGA DE ARCHIVOS
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
                self.btn_preview_econ.config(state=tk.NORMAL)
                self.econ_tab_built = False 
            else:
                self.filepath_pop = filepath
                self.df_pop_raw = df_temp
                self.lbl_status_pop.config(text=f"Población: 🟢 {name}", fg="green")
                self.btn_preview_pop.config(state=tk.NORMAL)
                self.pop_tab_built = False
                
            self.btn_prepare.config(state=tk.NORMAL)
            self.btn_process_all.config(state=tk.DISABLED)
        except Exception as e:
            messagebox.showerror("Error de Carga", f"Estructura incompatible:\n{str(e)}")

    # ---------------------------------------------------------
    # PASO 2: PREPARACIÓN DE ENTORNO E INTERSECCIÓN
    # ---------------------------------------------------------
    def prepare_environment(self):
        self.intersected_states.clear()
        self.intersected_muns.clear()
        
        pop_states, pop_muns, econ_states, econ_muns = {}, {}, {}, {}
        
        if self.df_pop_raw is not None:
            self.df_clean_pop = clean_geographic_data(self.df_pop_raw)
            clean_cols = {c: re.sub(r'^De\s+', '', str(c).strip(), flags=re.IGNORECASE) for c in self.df_clean_pop.columns}
            self.df_clean_pop.rename(columns=clean_cols, inplace=True)
            pop_states = extract_states_dict(self.df_clean_pop)
            for _, r in self.df_clean_pop[self.df_clean_pop['Codigo'].str.len() == 5].iterrows():
                pop_muns[r['Codigo']] = str(r['Entidad_Municipio']).strip()
                
        if self.df_econ_raw is not None:
            econ_muns = extract_economic_municipalities(self.df_econ_raw)
            ent_cols = [c for c in self.df_econ_raw.columns if 'ENTIDAD' in str(c).upper()]
            if ent_cols:
                for val in self.df_econ_raw[ent_cols[0]].dropna().unique():
                    match = re.match(r'^(\d{2})\s+(.*)$', str(val).strip())
                    if match and "NOTA" not in match.group(2).upper():
                        econ_states[match.group(1)] = match.group(2).strip()

        strict_mode = self.chk_intersection_var.get()
        if strict_mode and self.df_pop_raw is not None and self.df_econ_raw is not None:
            for code in pop_states:
                if code in econ_states:
                    mun_count = self.df_clean_pop[(self.df_clean_pop['Codigo'].str.len() == 5) & (self.df_clean_pop['Codigo'].str.startswith(code))].shape[0]
                    self.intersected_states[code] = f"🟢 {pop_states[code]}" if mun_count > 0 else f"⚪ {pop_states[code]}"
            for p_code, p_name in pop_muns.items():
                short_code = p_code[2:]
                if short_code in econ_muns and econ_muns[short_code].upper() in p_name.upper():
                    self.intersected_muns[p_code] = p_name
        else:
            base_states = pop_states if pop_states else {k: f"Entidad {k}" for k in econ_states}
            for code, name in base_states.items():
                m_count = self.df_clean_pop[(self.df_clean_pop['Codigo'].str.len() == 5) & (self.df_clean_pop['Codigo'].str.startswith(code))].shape[0] if self.df_pop_raw is not None else 1
                self.intersected_states[code] = f"🟢 {name}" if m_count > 0 else f"⚪ {name}"
                
            if pop_muns:
                self.intersected_muns = pop_muns
            elif econ_muns:
                st_code = list(econ_states.keys())[0] if len(econ_states) == 1 else "00"
                self.intersected_muns = {f"{st_code}{k}": v for k, v in econ_muns.items()}

        state_list = ["Toda la República Mexicana"] + [f"{k} - {v}" for k, v in self.intersected_states.items()]
        self.cb_estado['values'] = state_list
        if state_list:
            self.cb_estado.set(state_list[0])
            self.on_state_selected(None)
            
        if self.df_pop_raw is not None and not self.pop_tab_built:
            self.build_pop_tab()
            self.notebook.add(self.tab_pop, text="Análisis Demográfico")
            self.pop_tab_built = True
            
        if self.df_econ_raw is not None and not self.econ_tab_built:
            self.build_econ_tab()
            self.notebook.add(self.tab_econ, text="Censos Económicos")
            self.econ_tab_built = True
            
        self.btn_process_all.config(state=tk.NORMAL)
        messagebox.showinfo("Entorno Listo", "Entorno cargado y cruzado.\nSeleccione el Nivel Geográfico y proceda a Analizar.")

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
    # CONSTRUCCIÓN DE PESTAÑAS INTERNAS
    # ---------------------------------------------------------
    def build_pop_tab(self):
        for w in self.tab_pop.winfo_children(): w.destroy()
        
        filter_frame = tk.Frame(self.tab_pop)
        filter_frame.pack(fill=tk.X, pady=(0, 5))
        
        detected_year = extract_source_year(self.filepath_pop)
        tk.Label(filter_frame, text=f"Año Matriz: {detected_year}", font=("Arial", 9, "bold"), fg="blue").pack(side=tk.LEFT, padx=10)
        
        tk.Label(filter_frame, text="Filtro Rango de Edad:").pack(side=tk.LEFT, padx=15)
        self.cb_min_age = ttk.Combobox(filter_frame, state="readonly", width=12)
        self.cb_min_age.pack(side=tk.LEFT, padx=2)
        tk.Label(filter_frame, text="a").pack(side=tk.LEFT)
        self.cb_max_age = ttk.Combobox(filter_frame, state="readonly", width=12)
        self.cb_max_age.pack(side=tk.LEFT, padx=2)
        
        summary_frame = tk.Frame(self.tab_pop)
        summary_frame.pack(fill=tk.X, pady=(0, 5))
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
        filter_frame.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(filter_frame, text="Año Censal:").pack(side=tk.LEFT, padx=5)
        self.cb_year_econ = ttk.Combobox(filter_frame, state="readonly", width=8)
        self.cb_year_econ.pack(side=tk.LEFT, padx=5)
        
        tk.Label(filter_frame, text="Buscar:").pack(side=tk.LEFT, padx=15)
        self.txt_act_code = tk.Entry(filter_frame, width=20)
        self.txt_act_code.pack(side=tk.LEFT, padx=5)
        self.txt_act_code.bind("<KeyRelease>", self.filter_economic_realtime)
        
        # NUEVO CONTROL: Selector de Límite de Filas
        tk.Label(filter_frame, text="Mostrar filas:").pack(side=tk.LEFT, padx=15)
        self.cb_limit_econ = ttk.Combobox(filter_frame, state="readonly", width=8)
        self.cb_limit_econ['values'] = ["500", "1500", "5000", "10000", "Todos"]
        self.cb_limit_econ.set("1500")
        self.cb_limit_econ.pack(side=tk.LEFT, padx=5)
        # Sincronizado para actualizar la tabla instantáneamente al cambiar el valor
        self.cb_limit_econ.bind("<<ComboboxSelected>>", self.filter_economic_realtime)
        
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
    # PASO 3: ANÁLISIS DE INTERSECCIÓN Y DIBUJADO DE TABLAS
    # ---------------------------------------------------------
    def process_all_tabs(self):
        if self.df_pop_raw is not None: self.process_population()
        if self.df_econ_raw is not None: self.process_economic()

    def process_population(self):
        try:
            state_sel = self.cb_estado.get()
            mun_sel = self.cb_municipio.get()
            min_age, max_age = self.cb_min_age.get(), self.cb_max_age.get()
            cols = list(self.df_clean_pop.columns)
            age_cols = cols[cols.index(min_age):cols.index(max_age)+1]
            
            if "Toda la República" in state_sel:
                valid_codes = list(self.intersected_states.keys())
                state_data = self.df_clean_pop[self.df_clean_pop['Codigo'].isin(valid_codes)]
                mun_data = self.df_clean_pop[self.df_clean_pop['Codigo'].str.len() == 5]
            else:
                state_code = state_sel.replace("🟢 ", "").replace("⚪ ", "").split(" - ")[0]
                state_data_all, mun_data_all = get_state_and_municipalities(self.df_clean_pop, state_code)
                state_data = state_data_all
                
                if "Todos del Estado" in mun_sel:
                    mun_data = mun_data_all
                else:
                    mun_code = mun_sel.split(" - ")[0]
                    mun_data = mun_data_all[mun_data_all['Codigo'] == mun_code]
                    
            if state_data.empty: return
            
            t_ent = sum(pd.to_numeric(str(x).replace(',', ''), errors='coerce') or 0 for x in state_data['Total'].values)
            t_flt = sum(pd.to_numeric(str(x).replace(',', ''), errors='coerce') or 0 for col in age_cols for x in state_data[col].values)
            self.lbl_total_entidad.config(text=f"Población base (Padre): {t_ent:,.0f}")
            self.lbl_total_filtro.config(text=f"Población en rango: {t_flt:,.0f}")
            
            res_df = calculate_population_differences(state_data, mun_data, age_cols)
            self.render_tree(self.tree_pop, res_df, is_pop=True)
        except Exception as e:
            messagebox.showerror("Error en Demografía", f"Ocurrió un error procesando población:\n{str(e)}")

    def process_economic(self):
        try:
            state_sel = self.cb_estado.get()
            mun_sel = self.cb_municipio.get()
            target_year = self.cb_year_econ.get()
            self.txt_act_code.delete(0, tk.END)
            
            df_full = analyze_economic_hierarchy(self.df_econ_raw, None, target_year)
            if df_full.empty:
                self.df_econ_cache = df_full
                self.render_tree(self.tree_econ, self.df_econ_cache, is_pop=False)
                return

            if "Toda la República" in state_sel:
                self.df_econ_cache = df_full
            else:
                state_name = state_sel.replace("🟢 ", "").replace("⚪ ", "").split(" - ")[1].strip().upper()
                state_code = state_sel.replace("🟢 ", "").replace("⚪ ", "").split(" - ")[0]
                
                if "Todos del Estado" in mun_sel:
                    valid_mun_names = [v.upper() for k, v in self.intersected_muns.items() if k.startswith(state_code)]
                    valid_mun_names.append(state_name)
                    
                    if len(valid_mun_names) <= 1:
                        valid_mun_names = df_full['Ubicación'].str.upper().unique().tolist()
                        
                    self.df_econ_cache = df_full[df_full['Ubicación'].str.upper().isin(valid_mun_names)]
                else:
                    mun_name = mun_sel.split(" - ")[1].strip().upper()
                    self.df_econ_cache = df_full[df_full['Ubicación'].str.upper().isin([mun_name, state_name])]
                    
            self.render_tree(self.tree_econ, self.df_econ_cache, is_pop=False)
        except Exception as e:
            messagebox.showerror("Error en Censo Económico", f"Ocurrió un error estructurando los datos económicos:\n{str(e)}")

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

    def render_tree(self, tree, df, is_pop):
        tree.delete(*tree.get_children())
        if df.empty: return
        
        # --- LÍMITE CONTROLADO POR EL USUARIO ---
        display_df = df
        if not is_pop and hasattr(self, 'cb_limit_econ') and self.cb_limit_econ.winfo_exists():
            limite = self.cb_limit_econ.get()
            if limite != "Todos":
                try:
                    display_df = df.head(int(limite))
                except Exception:
                    pass
        
        tree["columns"] = list(display_df.columns)
        tree["show"] = "headings"
        
        for col in display_df.columns:
            max_len = len(str(col))
            for item in display_df[col]:
                item_str = f"{item:,.0f}" if isinstance(item, (int, float)) else str(item)
                if len(item_str) > max_len: max_len = len(item_str)
            
            align = "w" if col == 'Actividad Económica' else "center"
            
            if is_pop:
                w = (max_len * 8) + 12 if col == 'Municipio' else ((max_len * 9) + 10 if col == 'Cód. Mpio' else ((max_len * 7) + 4 if " a " in str(col) or "años" in str(col).lower() else (max_len * 7.5) + 6))
            else:
                if col == 'Actividad Económica': w = min(int((max_len * 6) + 4), 250)
                else: w = (max_len * 8) + 8 if 'Ubicación' in str(col) or 'Municipio' in str(col) else (max_len * 7.5) + 4
                
            tree.heading(col, text=col)
            tree.column(col, width=int(w), minwidth=int(w), stretch=tk.NO, anchor=align)
            
        for _, row in display_df.iterrows():
            vals = [f"{item:,.0f}" if isinstance(item, (int, float)) else item for item in list(row)]
            tree.insert("", "end", values=vals)