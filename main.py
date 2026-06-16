# main.py
import tkinter as tk
from ui.main_window import MainWindow

def main():
    """
    Punto de entrada principal de la aplicación.
    Inicializa la ventana de la interfaz gráfica.
    """
    root = tk.Tk()
    root.title("INEGI Data Extractor")
    # Tamaño inicial de la ventana
    root.geometry("900x600")
    app = MainWindow(root)
    root.mainloop()

if __name__ == "__main__":
    main()