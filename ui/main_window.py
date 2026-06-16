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
        
        self.filepath_pop = None
        self.df_pop = None
        
        self.filepath_econ = None
        self.df_econ = None
        self.df_econ_cache = None 
        
        self.setup_ui()
        
    def setup_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.tab_pop = tk.Frame(self.notebook, padx=15, pady=15)
        self.notebook.add(self.tab_pop, text="Análisis de Población")
        self.setup_population_tab()
        
        self.tab_econ = tk.Frame(self.notebook, padx=15, pady=15)
        self.notebook.add(self.tab_econ, text="Censos Económicos")
        self.setup_economic_tab()

    def setup_population_tab(self):
        file_frame = tk.LabelFrame(self.tab_pop, text=" Matriz de Población ", padx=10, pady=5)
        file_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=5)
        
        self.btn_load_pop = tk.Button(file_frame, text="Cargar Archivo de Población", command=self.load_population_file)
        self.btn_load_pop.grid(row=0, column=0, pady=5)
        self.lbl_file_pop = tk.Label(file_frame, text="Ningún archivo cargado.", font=("Arial", 9, "italic"))
        self.lbl_file_pop.grid(row=0, column=1, padx=10)
        self.btn_preview_pop = tk.Button(file_frame, text="Previsualizar", state=tk.DISABLED, command=lambda: open_file_in_system(self.filepath_pop))
        self.btn_preview_pop.grid(row=0, column=2)

        filter_frame = tk.Frame(self.tab_pop)
        filter_frame.grid(row=1, column=0, columnspan=3, pady=10, sticky="w")
        
        # Etiqueta de Año leída del documento (sin desplegable)
        self.lbl_year_pop = tk.Label(filter_frame, text="Año de la matriz: -", font=("Arial", 9, "bold"), fg="blue")
        self.lbl_year_pop.grid(row=0, column=0, padx=10)
        
        tk.Label(filter_frame, text="Estado:").grid(row=0, column=1, padx=5)
        self.cb_state = ttk.Combobox(filter_frame, state="readonly", width=35)
        self.cb_state.grid(row=0, column=2, padx=5)
        
        tk.Label(filter_frame, text="Rango:").grid(row=0, column=3, padx=5)
        self.cb_min_age = ttk.Combobox(filter_frame, state="readonly", width=12)
        self.cb_min_age.grid(row=0, column=4, padx=2)
        tk.Label(filter_frame, text="a").grid(row=0, column=5)
        self.cb_max_age = ttk.Combobox(filter_frame, state="readonly", width=12)
        self.cb_max_age.grid(row=0, column=6, padx=2)
        
        self.btn_process_pop = tk.Button(self.tab_pop, text="Procesar Datos", state=tk.DISABLED, command=self.process_population)
        self.btn_process_pop.grid(row=2, column=0, columnspan=3, pady=5)
        
        self.lbl_total_entidad = tk.Label(self.tab_pop, text="Población total de la entidad: -", font=("Arial", 9, "bold"))
        self.lbl_total_entidad.grid(row=3, column=0, columnspan=3, pady=2, sticky="w")
        self.lbl_total_filtro = tk.Label(self.tab_pop, text="Población total dentro del filtro: -", font=("Arial", 9, "bold"))
        self.lbl_total_filtro.grid(row=4, column=0, columnspan=3, pady=2, sticky="w")
        
        self.tree_pop = ttk.Treeview(self.tab_pop)
        self.tree_pop.grid(row=5, column=0, columnspan=3, sticky="nsew")
        self.configure_scrollbars(self.tab_pop, self.tree_pop, row=5)

    def setup_economic_tab(self):
        file_frame = tk.LabelFrame(self.tab_econ, text=" Matriz de Censos Económicos ", padx=10, pady=5)
        file_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=5)
        
        self.btn_load_econ = tk.Button(file_frame, text="Cargar Archivo Económico", command=self.load_economic_file)
        self.btn_load_econ.grid(row=0, column=0, pady=5)
        self.lbl_file_econ = tk.Label(file_frame, text="Ningún archivo cargado.", font=("Arial", 9, "italic"))
        self.lbl_file_econ.grid(row=0, column=1, padx=10)
        self.btn_preview_econ = tk.Button(file_frame, text="Previsualizar", state=tk.DISABLED, command=lambda: open_file_in_system(self.filepath_econ))
        self.btn_preview_econ.grid(row=0, column=2)

        filter_frame = tk.Frame(self.tab_econ)
        filter_frame.grid(row=1, column=0, columnspan=3, pady=10, sticky="w")
        
        # Desplegables alimentados directamente de la matriz
        tk.Label(filter_frame, text="Año:").grid(row=0, column=0, padx=5)
        self.cb_year_econ = ttk.Combobox(filter_frame, state="readonly", width=8)
        self.cb_year_econ.grid(row=0, column=1, padx=5)
        
        tk.Label(filter_frame, text="Municipio:").grid(row=0, column=2, padx=5)
        self.cb_mun_econ = ttk.Combobox(filter_frame, state="readonly", width=30)
        self.cb_mun_econ.grid(row=0, column=3, padx=5)
        
        # Filtro de clave con evento de tecleo en tiempo real
        tk.Label(filter_frame, text="Filtro de Jerarquía (Realtime):").grid(row=0, column=4, padx=5)
        self.txt_act_code = tk.Entry(filter_frame, width=15)
        self.txt_act_code.grid(row=0, column=5, padx=5)
        self.txt_act_code.bind("<KeyRelease>", self.filter_economic_realtime)
        
        self.btn_process_econ = tk.Button(self.tab_econ, text="Extraer y Estructurar", state=tk.DISABLED, command=self.process_economic)
        self.btn_process_econ.grid(row=2, column=0, columnspan=3, pady=5)
        
        self.tree_econ = ttk.Treeview(self.tab_econ)
        self.tree_econ.grid(row=3, column=0, columnspan=3, sticky="nsew")
        self.configure_scrollbars(self.tab_econ, self.tree_econ, row=3)

    def configure_scrollbars(self, parent, tree, row):
        parent.rowconfigure(row, weight=1)
        parent.columnconfigure(1, weight=1)
        scy = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scy.set)
        scy.grid(row=row, column=3, sticky='ns')
        scx = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(xscroll=scx.set)
        scx.grid(row=row+1, column=0, columnspan=3, sticky='ew')

    # --- FLUJOS DE CARGA ---
    def load_population_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Archivos", "*.csv *.xlsx *.xls")])
        if not filepath: return
        try:
            self.filepath_pop = filepath
            self.lbl_file_pop.config(text=filepath.split('/')[-1])
            
            # Obtiene el año de forma orgánica y actualiza la etiqueta
            detected_year = extract_source_year(filepath)
            self.lbl_year_pop.config(text=f"Año de la matriz: {detected_year}")
            
            self.df_pop = load_inegi_data(self.filepath_pop)
            self.df_clean_pop = clean_geographic_data(self.df_pop)
            
            clean_cols = {c: re.sub(r'^De\s+', '', str(c).strip(), flags=re.IGNORECASE) for c in self.df_clean_pop.columns}
            self.df_clean_pop.rename(columns=clean_cols, inplace=True)
            
            states = extract_states_dict(self.df_clean_pop)
            self.cb_state['values'] = [f"{k} - {v}" for k, v in states.items()]
            if states: self.cb_state.set(self.cb_state['values'][0])
            
            age_cols = [c for c in self.df_clean_pop.columns if re.search(r'años|\d+\s+a\s+\d+', str(c), re.IGNORECASE)]
            self.cb_min_age['values'] = age_cols
            self.cb_max_age['values'] = age_cols
            if '15 a 19 años' in age_cols: self.cb_min_age.set('15 a 19 años')
            if '60 a 64 años' in age_cols: self.cb_max_age.set('60 a 64 años')
            
            self.btn_preview_pop.config(state=tk.NORMAL)
            self.btn_process_pop.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Error", f"Fallo al cargar:\n{str(e)}")

    def load_economic_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Archivos", "*.csv *.xlsx *.xls")])
        if not filepath: return
        try:
            self.filepath_econ = filepath
            self.lbl_file_econ.config(text=filepath.split('/')[-1])
            
            self.df_econ = load_inegi_data(self.filepath_econ)
            
            years = extract_economic_years(self.df_econ)
            if years:
                self.cb_year_econ['values'] = years
                self.cb_year_econ.set(years[0])
            
            municipalities = extract_economic_municipalities(self.df_econ)
            mun_options = ["TODOS"] + [f"{k} - {v}" for k, v in municipalities.items()]
            self.cb_mun_econ['values'] = mun_options
            self.cb_mun_econ.set(mun_options[0])
            
            self.btn_preview_econ.config(state=tk.NORMAL)
            self.btn_process_econ.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Error", f"Fallo al cargar:\n{str(e)}")

    # --- FLUJOS DE PROCESAMIENTO ---
    def process_population(self):
        try:
            state_str = self.cb_state.get()
            min_age, max_age = self.cb_min_age.get(), self.cb_max_age.get()
            state_code = state_str.split(" - ")[0]
            
            cols = list(self.df_clean_pop.columns)
            age_cols = cols[cols.index(min_age):cols.index(max_age)+1]
            state_data, mun_data = get_state_and_municipalities(self.df_clean_pop, state_code)
            
            total_entidad = pd.to_numeric(str(state_data['Total'].values[0]).replace(',', ''), errors='coerce') or 0
            total_filtro = sum(pd.to_numeric(str(state_data[col].values[0]).replace(',', ''), errors='coerce') or 0 for col in age_cols)
            
            self.lbl_total_entidad.config(text=f"Población total de la entidad: {total_entidad:,.0f}")
            self.lbl_total_filtro.config(text=f"Población total dentro del filtro: {total_filtro:,.0f}")
            
            if mun_data.empty:
                messagebox.showinfo("Aviso", "Estado sin municipios desglosados.")
                return
                
            res_df = calculate_population_differences(state_data, mun_data, age_cols)
            self.render_tree(self.tree_pop, res_df, is_pop=True)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def process_economic(self):
        try:
            mun_str = self.cb_mun_econ.get()
            target_mun = None if "TODOS" in mun_str else mun_str.split(" - ")[0]
            target_year = self.cb_year_econ.get()
            
            # Limpiar caja de texto realtime al procesar un nuevo set
            self.txt_act_code.delete(0, tk.END)
            
            self.df_econ_cache = analyze_economic_hierarchy(self.df_econ, target_mun, target_year)
            
            if self.df_econ_cache.empty:
                messagebox.showwarning("Aviso", "No hay datos para este corte.")
                self.tree_econ.delete(*self.tree_econ.get_children())
                return
                
            self.render_tree(self.tree_econ, self.df_econ_cache, is_pop=False)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def filter_economic_realtime(self, event):
        """Actualiza la tabla al instante comparando el texto con la jerarquía Clave."""
        if self.df_econ_cache is None or self.df_econ_cache.empty:
            return
            
        search = self.txt_act_code.get().strip()
        if search == "":
            self.render_tree(self.tree_econ, self.df_econ_cache, is_pop=False)
        else:
            filtered = self.df_econ_cache[self.df_econ_cache['Clave'].astype(str).str.startswith(search)]
            self.render_tree(self.tree_econ, filtered, is_pop=False)

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
            
            if is_pop:
                w = (max_len * 8) + 12 if col == 'Municipio' else ((max_len * 9) + 10 if col == 'Cód. Mpio' else ((max_len * 7) + 4 if " a " in str(col) or "años" in str(col).lower() else (max_len * 7.5) + 6))
            else:
                # Ajuste ceñido para la tabla económica
                w = (max_len * 7.5) + 6 if 'Actividad' in str(col) else ((max_len * 8) + 8 if 'Ubicación' in str(col) else (max_len * 7.5) + 4)
                
            tree.heading(col, text=col)
            tree.column(col, width=int(w), minwidth=int(w), stretch=tk.NO, anchor="center")
            
        for _, row in df.iterrows():
            vals = [f"{item:,.0f}" if isinstance(item, (int, float)) else item for item in list(row)]
            tree.insert("", "end", values=vals)