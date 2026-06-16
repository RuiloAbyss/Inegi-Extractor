# ui/main_window.py

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import re
from core.file_manager import load_inegi_data, open_file_in_system
from processors.location_manager import clean_geographic_data, extract_states_dict, get_state_and_municipalities
from processors.working_age_calculator import calculate_population_differences

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.filepath = None       
        self.df = None             
        self.df_clean = None       
        self.states_dict = {}      
        self.setup_ui()
        
    def setup_ui(self):
        frame = tk.Frame(self.root, padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        self.btn_load = tk.Button(frame, text="Load File (Cargar)", command=self.load_file)
        self.btn_load.grid(row=0, column=0, pady=5, sticky="w")
        
        self.lbl_file = tk.Label(frame, text="Ningún archivo cargado.")
        self.lbl_file.grid(row=0, column=1, pady=5, padx=10, sticky="w")
        
        self.btn_preview = tk.Button(frame, text="Preview File (Previsualizar)", state=tk.DISABLED, command=self.preview_file)
        self.btn_preview.grid(row=0, column=2, padx=10, pady=5, sticky="w")
        
        tk.Label(frame, text="Select State (Estado):").grid(row=1, column=0, pady=5, sticky="w")
        self.cb_state = ttk.Combobox(frame, state="readonly", width=40)
        self.cb_state.grid(row=1, column=1, columnspan=2, pady=5, sticky="w")
        
        tk.Label(frame, text="Min Age Group:").grid(row=2, column=0, pady=5, sticky="w")
        self.cb_min_age = ttk.Combobox(frame, state="readonly", width=30)
        self.cb_min_age.grid(row=2, column=1, columnspan=2, pady=5, sticky="w")
        
        tk.Label(frame, text="Max Age Group:").grid(row=3, column=0, pady=5, sticky="w")
        self.cb_max_age = ttk.Combobox(frame, state="readonly", width=30)
        self.cb_max_age.grid(row=3, column=1, columnspan=2, pady=5, sticky="w")
        
        self.btn_process = tk.Button(frame, text="Process Data (Procesar)", state=tk.DISABLED, command=self.process_data)
        self.btn_process.grid(row=4, column=0, columnspan=3, pady=15)
        
        self.lbl_total_entidad = tk.Label(frame, text="Población total de la entidad: -", font=("Arial", 10, "bold"))
        self.lbl_total_entidad.grid(row=5, column=0, columnspan=3, pady=2, sticky="w")
        
        self.lbl_total_filtro = tk.Label(frame, text="Población total dentro del filtro de edad: -", font=("Arial", 10, "bold"))
        self.lbl_total_filtro.grid(row=6, column=0, columnspan=3, pady=2, sticky="w")
        
        self.tree = ttk.Treeview(frame)
        self.tree.grid(row=7, column=0, columnspan=3, sticky="nsew")
        
        frame.rowconfigure(7, weight=1)
        frame.columnconfigure(1, weight=1)
        
        scrollbar_y = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar_y.set)
        scrollbar_y.grid(row=7, column=3, sticky='ns')
        
        scrollbar_x = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(xscroll=scrollbar_x.set)
        scrollbar_x.grid(row=8, column=0, columnspan=3, sticky='ew')
        
    def load_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx *.xls")])
        if not filepath:
            return
            
        try:
            self.filepath = filepath
            self.lbl_file.config(text=filepath.split('/')[-1])
            self.btn_preview.config(state=tk.NORMAL)
            
            self.df = load_inegi_data(self.filepath)
            self.df_clean = clean_geographic_data(self.df)
            
            clean_cols = {}
            for col in self.df_clean.columns:
                clean_cols[col] = re.sub(r'^De\s+', '', str(col).strip(), flags=re.IGNORECASE)
            self.df_clean.rename(columns=clean_cols, inplace=True)
            
            self.states_dict = extract_states_dict(self.df_clean)
            state_options = [f"{code} - {name}" for code, name in self.states_dict.items()]
            self.cb_state['values'] = state_options
            if state_options:
                self.cb_state.set(state_options[0])
            
            cols = list(self.df_clean.columns)
            age_columns = []
            
            for col in cols:
                if re.search(r'años|\d+\s+a\s+\d+', str(col), re.IGNORECASE):
                    age_columns.append(col)
                    
            if not age_columns:
                messagebox.showwarning("Aviso", "No se detectaron columnas de edad con el formato esperado.")
                return
                
            self.cb_min_age['values'] = age_columns
            self.cb_max_age['values'] = age_columns
            
            if '15 a 19 años' in age_columns:
                self.cb_min_age.set('15 a 19 años')
            else:
                self.cb_min_age.set(age_columns[0])
                
            if '60 a 64 años' in age_columns:
                self.cb_max_age.set('60 a 64 años')
            else:
                self.cb_max_age.set(age_columns[-1])
                
            self.btn_process.config(state=tk.NORMAL)
            
        except Exception as e:
            messagebox.showerror("Error al cargar", f"Ocurrió un problema procesando el archivo:\n{str(e)}")
            
    def preview_file(self):
        if self.filepath:
            open_file_in_system(self.filepath)
            
    def process_data(self):
        selected_state_str = self.cb_state.get()
        min_age = self.cb_min_age.get()
        max_age = self.cb_max_age.get()
        
        if not selected_state_str or not min_age or not max_age:
            messagebox.showwarning("Warning", "Asegúrate de seleccionar el Estado y los rangos de edad.")
            return
            
        try:
            state_code = selected_state_str.split(" - ")[0]
            state_name = selected_state_str.split(" - ")[1].upper()
            
            cols = list(self.df_clean.columns)
            start_idx = cols.index(min_age)
            end_idx = cols.index(max_age)
            
            if start_idx > end_idx:
                messagebox.showerror("Error", "La edad mínima no puede ser mayor que la edad máxima.")
                return
                
            age_cols = cols[start_idx : end_idx + 1]
            state_data, mun_data = get_state_and_municipalities(self.df_clean, state_code)
            
            if state_data.empty:
                messagebox.showerror("Error", "No se encontraron registros para el estado seleccionado.")
                return

            raw_total_state = str(state_data['Total'].values[0]).replace(',', '')
            total_entidad = pd.to_numeric(raw_total_state, errors='coerce') or 0
            
            total_filtro = 0
            for col in age_cols:
                raw_val = str(state_data[col].values[0]).replace(',', '')
                total_filtro += pd.to_numeric(raw_val, errors='coerce') or 0
                
            self.lbl_total_entidad.config(text=f"Población total de la entidad: {total_entidad:,.0f}")
            self.lbl_total_filtro.config(text=f"Población total dentro del filtro de edad: {total_filtro:,.0f}")
            
            if mun_data.empty:
                messagebox.showinfo("Aviso", f"{state_name} no tiene desglosado los municipios.")
                return
                
            result_df = calculate_population_differences(state_data, mun_data, age_cols)
            self.display_results(result_df)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error en el procesamiento:\n{str(e)}")
            
    def display_results(self, df):
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = list(df.columns)
        self.tree["show"] = "headings"
        
        # CALIBRACIÓN DE ANCHOS DE COLUMNA EXACTOS
        for col in df.columns:
            max_len = len(str(col))
            
            for item in df[col]:
                if isinstance(item, (int, float)):
                    item_str = f"{item:,.0f}"
                else:
                    item_str = str(item)
                if len(item_str) > max_len:
                    max_len = len(item_str)
            
            # Ajustes milimétricos según el tipo de columna solicitado
            if col == 'Municipio':
                # "Apenas un poco más que su municipio con el nombre más largo"
                col_width = (max_len * 8) + 12  
            elif col == 'Cód. Mpio':
                # Ajustado adecuadamente al tamaño de la cifra del código
                col_width = (max_len * 9) + 10  
            elif " a " in str(col) or "años" in str(col).lower():
                # "Casi nada de espacio horizontal extra" -> Súper compacto
                col_width = (max_len * 7) + 4   
            else:
                # Para la "Cantidad de personas en rango" (Usa un ancho ceñido al texto de cabecera)
                col_width = (max_len * 7.5) + 6 
            
            self.tree.heading(col, text=col)
            self.tree.column(col, width=int(col_width), minwidth=int(col_width), stretch=tk.NO, anchor="center")
            
        for index, row in df.iterrows():
            formatted_values = []
            for item in list(row):
                if isinstance(item, (int, float)):
                    formatted_values.append(f"{item:,.0f}")
                else:
                    formatted_values.append(item)
            self.tree.insert("", "end", values=formatted_values)