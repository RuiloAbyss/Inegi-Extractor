# ui/main_window.py

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from core.file_manager import load_inegi_data, open_file_in_system
from processors.location_manager import clean_geographic_data, extract_states_dict, get_state_and_municipalities
from processors.working_age_calculator import calculate_population_differences

class MainWindow:
    """
    Clase principal de la interfaz gráfica (UI) para la aplicación INEGI Data Extractor.
    
    Se encarga de la gestión de la ventana, la disposición de los componentes visuales 
    (Tkinter/TTK), la captura de eventos del usuario y la interacción directa con los 
    módulos de procesamiento geográfico y matemático.
    """

    def __init__(self, root):
        """
        Inicializa la ventana principal y define el estado inicial de las variables de datos.
        
        Parámetros:
        - root (tk.Tk): Instancia de la ventana raíz de Tkinter.
        """
        self.root = root
        self.filepath = None       # Ruta absoluta del archivo cargado (.csv o .xlsx)
        self.df = None             # DataFrame original sin procesar
        self.df_clean = None       # DataFrame filtrado y normalizado geográficamente
        self.states_dict = {}      # Diccionario de estados disponibles {código: nombre}
        
        # Inicialización de los componentes de la interfaz
        self.setup_ui()
        
    def setup_ui(self):
        """
        Construye y organiza todos los elementos widgets en la ventana.
        
        Dispone los botones de carga y previsualización, los menús desplegables 
        (Combobox) para la selección jerárquica del Estado y los rangos de edad, 
        así como la tabla de visualización de datos (Treeview) con sus respectivas 
        barras de desplazamiento.
        """
        # Contenedor principal con márgenes internos
        frame = tk.Frame(self.root, padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Fila de controles de archivos (Botón cargar, etiqueta de ruta, botón previsualizar)
        self.btn_load = tk.Button(frame, text="Load File (Cargar)", command=self.load_file)
        self.btn_load.grid(row=0, column=0, pady=5, sticky="w")
        
        self.lbl_file = tk.Label(frame, text="Ningún archivo cargado.")
        self.lbl_file.grid(row=0, column=1, pady=5, padx=10, sticky="w")
        
        self.btn_preview = tk.Button(frame, text="Preview File (Previsualizar)", state=tk.DISABLED, command=self.preview_file)
        self.btn_preview.grid(row=0, column=2, padx=10, pady=5, sticky="w")
        
        # Control de Selección Geográfica (Desplegable para elegir el Estado)
        tk.Label(frame, text="Select State (Estado):").grid(row=1, column=0, pady=5, sticky="w")
        self.cb_state = ttk.Combobox(frame, state="readonly", width=40)
        self.cb_state.grid(row=1, column=1, columnspan=2, pady=5, sticky="w")
        
        # Controles de Selección de Rango de Edad (Desplegables para Edad Mínima y Máxima)
        tk.Label(frame, text="Min Age Group:").grid(row=2, column=0, pady=5, sticky="w")
        self.cb_min_age = ttk.Combobox(frame, state="readonly", width=30)
        self.cb_min_age.grid(row=2, column=1, columnspan=2, pady=5, sticky="w")
        
        tk.Label(frame, text="Max Age Group:").grid(row=3, column=0, pady=5, sticky="w")
        self.cb_max_age = ttk.Combobox(frame, state="readonly", width=30)
        self.cb_max_age.grid(row=3, column=1, columnspan=2, pady=5, sticky="w")
        
        # Botón de ejecución del procesamiento matemático
        self.btn_process = tk.Button(frame, text="Process Data (Procesar)", state=tk.DISABLED, command=self.process_data)
        self.btn_process.grid(row=4, column=0, columnspan=3, pady=20)
        
        # Tabla de resultados (Treeview) configurada con barras de desplazamiento X e Y
        self.tree = ttk.Treeview(frame)
        self.tree.grid(row=5, column=0, columnspan=3, sticky="nsew")
        
        # Configuración de expansión elástica para la tabla
        frame.rowconfigure(5, weight=1)
        frame.columnconfigure(1, weight=1)
        
        scrollbar_y = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar_y.set)
        scrollbar_y.grid(row=5, column=3, sticky='ns')
        
        scrollbar_x = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(xscroll=scrollbar_x.set)
        scrollbar_x.grid(row=6, column=0, columnspan=3, sticky='ew')
        
    def load_file(self):
        """
        Maneja el evento de selección y apertura de archivos de datos del INEGI.
        """
        filepath = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx *.xls")]
        )
        if not filepath:
            return
            
        try:
            self.filepath = filepath
            self.lbl_file.config(text=filepath.split('/')[-1])
            self.btn_preview.config(state=tk.NORMAL)
            
            # Carga y filtrado inicial usando el ecosistema modular
            self.df = load_inegi_data(self.filepath)
            self.df_clean = clean_geographic_data(self.df)
            
            # Extracción geográfica para el ComboBox
            self.states_dict = extract_states_dict(self.df_clean)
            state_options = [f"{code} - {name}" for code, name in self.states_dict.items()]
            self.cb_state['values'] = state_options
            if state_options:
                self.cb_state.set(state_options[0])
            
            # --- NUEVA LÓGICA ROBUSTA PARA ENCONTRAR COLUMNAS DE EDAD ---
            import re
            cols = list(self.df_clean.columns)
            age_columns = []
            
            for col in cols:
                # Buscamos columnas que contengan la palabra "años" (ignorando mayúsculas)
                # o el patrón "De X a Y"
                if re.search(r'años|de\s+\d+\s+a\s+\d+', str(col), re.IGNORECASE):
                    age_columns.append(col)
                    
            if not age_columns:
                messagebox.showwarning("Aviso", "No se detectaron columnas de edad con el formato esperado ('De X a Y años'). Verifica el archivo.")
                return
                
            self.cb_min_age['values'] = age_columns
            self.cb_max_age['values'] = age_columns
            
            # Selección inteligente por defecto
            if 'De 15 a 19 años' in age_columns:
                self.cb_min_age.set('De 15 a 19 años')
            else:
                self.cb_min_age.set(age_columns[0]) # Selecciona la primera si no halla la de 15
                
            if 'De 60 a 64 años' in age_columns:
                self.cb_max_age.set('De 60 a 64 años')
            else:
                self.cb_max_age.set(age_columns[-1]) # Selecciona la última si no halla la de 64
                
            self.btn_process.config(state=tk.NORMAL)
            
        except Exception as e:
            messagebox.showerror("Error al cargar", f"Ocurrió un problema procesando el archivo:\n{str(e)}")
    
    def preview_file(self):
        """
        Invoca la herramienta externa del sistema operativo para revisar el archivo en crudo.
        
        Llama al procedimiento del sistema que abre el archivo actual con la aplicación 
        predeterminada (por ejemplo, Microsoft Excel, LibreOffice Calc o el bloc de notas) 
        sin bloquear la ejecución de la interfaz gráfica.
        """
        if self.filepath:
            open_file_in_system(self.filepath)
            
    def process_data(self):
        """
        Orquesta el flujo de filtrado geográfico y cálculo numérico tras la orden del usuario.
        
        Procedimiento:
        1. Obtiene el Estado seleccionado y extrae su clave numérica de dos dígitos.
        2. Obtiene los límites de edad seleccionados y mapea las columnas correspondientes de la matriz.
        3. Segmenta los datos obteniendo la fila del Estado y únicamente las de sus municipios asociados.
        4. Si el archivo no contiene el desglose municipal para esa entidad, notifica al usuario.
        5. Envía los segmentos al calculador matemático para procesar las poblaciones en rango, 
           fuera de rango y ejecutar las diferencias solicitadas para la fórmula.
        6. Envía el resultado final estructurado a la pantalla.
        """
        selected_state_str = self.cb_state.get()
        min_age = self.cb_min_age.get()
        max_age = self.cb_max_age.get()
        
        if not selected_state_str or not min_age or not max_age:
            messagebox.showwarning("Warning", "Asegúrate de seleccionar el Estado y los rangos de edad.")
            return
            
        try:
            state_code = selected_state_str.split(" - ")[0]
            cols = list(self.df_clean.columns)
            start_idx = cols.index(min_age)
            end_idx = cols.index(max_age)
            
            if start_idx > end_idx:
                messagebox.showerror("Error", "La edad mínima no puede ser mayor que la edad máxima.")
                return
                
            age_cols = cols[start_idx : end_idx + 1]
            
            # Segmentación de datos mediante location_manager
            state_data, mun_data = get_state_and_municipalities(self.df_clean, state_code)
            
            if mun_data.empty:
                messagebox.showinfo("Info", "El archivo actual no contiene el desglose de municipios para esta entidad.")
                return
                
            # Procesamiento matemático core
            result_df = calculate_population_differences(state_data, mun_data, age_cols)
            self.display_results(result_df)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error en el procesamiento:\n{str(e)}")
            
    def display_results(self, df):
        """
        Actualiza y renderiza un DataFrame de Pandas dentro de la tabla visual Treeview.
        
        Limpia las filas preexistentes, reconfigura dinámicamente las columnas y 
        encabezados según la estructura de salida del procedimiento ejecutado, e 
        inserta los nuevos registros numéricos formateados para su visualización inmediata.
        
        Parámetros:
        - df (pd.DataFrame): Matriz de datos procesados con los resultados por municipio.
        """
        self.tree.delete(*self.tree.get_children())
        self.tree["column"] = list(df.columns)
        self.tree["show"] = "headings"
        
        for col in self.tree["column"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=125, anchor="center")
            
        for index, row in df.iterrows():
            # Formatear números con comas para la presentación final en la UI
            formatted_values = []
            for item in list(row):
                if isinstance(item, (int, float)):
                    formatted_values.append(f"{item:,.0f}")
                else:
                    formatted_values.append(item)
            self.tree.insert("", "end", values=formatted_values)