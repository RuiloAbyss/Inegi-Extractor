# processors/export_manager.py
import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd

class ExportManager:
    @staticmethod
    def open_export_window(parent, tree_pop, tree_econ, tree_calc, pop_year, econ_year, env_prepared):
        if not env_prepared:
            messagebox.showerror("Error de Validación", "Debe preparar el entorno y analizar los datos antes de poder exportarlos.")
            return

        top = tk.Toplevel(parent)
        top.title("Exportación de Análisis - Excel")
        top.geometry("480x350")
        top.resizable(False, False)
        top.grab_set()

        tk.Label(top, text="Seleccione las tablas que desea exportar:", font=("Arial", 10, "bold")).pack(pady=10)

        # Checkboxes para seleccionar pestañas
        var_pop = tk.BooleanVar(value=True)
        var_econ = tk.BooleanVar(value=True)
        var_calc = tk.BooleanVar(value=True)

        tk.Checkbutton(top, text="1. Análisis Demográfico (Población / Extrapolación)", variable=var_pop, font=("Arial", 9)).pack(anchor="w", padx=40, pady=2)
        tk.Checkbutton(top, text="2. Censos Económicos (SAIC)", variable=var_econ, font=("Arial", 9)).pack(anchor="w", padx=40, pady=2)
        tk.Checkbutton(top, text="3. Cálculos de Inteligencia (Clusters)", variable=var_calc, font=("Arial", 9)).pack(anchor="w", padx=40, pady=2)

        # Panel de Advertencias exigido
        warn_frame = tk.LabelFrame(top, text=" ⚠️ Advertencias Importantes de Integridad ", fg="#d35400", font=("Arial", 9, "bold"))
        warn_frame.pack(fill=tk.X, padx=15, pady=15)

        tk.Label(warn_frame, text="• Formato Diferente: Las exportaciones son resúmenes estructurados \n  y procesados; manejan un formato que podría no ser compatible \n  con algunos lectores crudos orientados al formato base del INEGI.", 
                 font=("Arial", 8, "italic"), justify=tk.LEFT, fg="#555555").pack(anchor="w", padx=5, pady=5)

        # Validación visual del desfase de años
        if pop_year and econ_year and str(pop_year) != str(econ_year):
            tk.Label(warn_frame, text=f"• ¡Desfase Detectado!: Población ({pop_year}) vs Economía ({econ_year}).\n  Tenga en cuenta esta imprecisión temporal en su reporte final.", 
                     font=("Arial", 8, "bold"), justify=tk.LEFT, fg="#e67e22").pack(anchor="w", padx=5, pady=2)
        elif not pop_year or not econ_year:
            tk.Label(warn_frame, text="• Información incompleta: Asegúrese de tener ambos censos analizados.", 
                     font=("Arial", 8, "bold"), justify=tk.LEFT, fg="#c0392b").pack(anchor="w", padx=5, pady=2)
        else:
            tk.Label(warn_frame, text="• Temporalidad alineada correctamente.", 
                     font=("Arial", 8, "bold"), justify=tk.LEFT, fg="#27ae60").pack(anchor="w", padx=5, pady=2)

        def execute_export():
            if not (var_pop.get() or var_econ.get() or var_calc.get()):
                messagebox.showwarning("Atención", "Debe seleccionar al menos una pestaña para exportar.")
                return

            # FORMATO DE NOMBRE POR DEFECTO EXIGIDO
            default_filename = f"analisis_cluster_{econ_year}.xlsx" if econ_year else "analisis_cluster.xlsx"

            filepath = filedialog.asksaveasfilename(
                initialfile=default_filename,
                defaultextension=".xlsx",
                filetypes=[("Libro de Excel", "*.xlsx")],
                title="Guardar Exportación Múltiple"
            )
            if not filepath: return

            try:
                with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                    if var_pop.get():
                        df_pop = ExportManager._treeview_to_dataframe(tree_pop)
                        if not df_pop.empty: df_pop.to_excel(writer, sheet_name="Demográfico", index=False)
                        else: pd.DataFrame({"Aviso": ["Sin datos procesados en Demografía"]}).to_excel(writer, sheet_name="Demográfico", index=False)
                            
                    if var_econ.get():
                        df_econ = ExportManager._treeview_to_dataframe(tree_econ)
                        if not df_econ.empty: df_econ.to_excel(writer, sheet_name="Económico", index=False)
                        else: pd.DataFrame({"Aviso": ["Sin datos procesados en Económico"]}).to_excel(writer, sheet_name="Económico", index=False)

                    if var_calc.get():
                        df_calc = ExportManager._treeview_to_dataframe(tree_calc)
                        if not df_calc.empty: df_calc.to_excel(writer, sheet_name="Clusters", index=False)
                        else: pd.DataFrame({"Aviso": ["Sin cálculos generados"]}).to_excel(writer, sheet_name="Clusters", index=False)

                messagebox.showinfo("Exportación Exitosa", f"El archivo Excel ha sido creado con éxito:\n{filepath}")
                top.destroy()
            except Exception as e:
                messagebox.showerror("Error al Exportar", f"Hubo un problema guardando el archivo. Asegúrese de que no esté abierto.\n\nDetalle: {str(e)}")

        btn_frame = tk.Frame(top)
        btn_frame.pack(fill=tk.X, pady=5)
        tk.Button(btn_frame, text="Guardar Excel", command=execute_export, font=("Arial", 10, "bold"), bg="#27ae60", fg="white", width=20).pack(side=tk.TOP, pady=5)

    @staticmethod
    def _treeview_to_dataframe(tree):
        """Convierte el contenido visual de un Treeview de Tkinter en un DataFrame de Pandas."""
        columns = tree["columns"]
        if not columns: return pd.DataFrame()
        
        rows = []
        for item in tree.get_children():
            rows.append(tree.item(item)["values"])
            
        return pd.DataFrame(rows, columns=columns)