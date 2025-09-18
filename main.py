import tkinter as tk
from gui_main import App

def main():
    # 1. Crea la ventana principal de Tkinter
    root = tk.Tk()
    # 2. Crea una instancia de nuestra aplicación, pasándole la ventana raíz
    app = App(root)
    # 3. Inicia el bucle principal de la GUI
    root.mainloop()


if __name__ == "__main__":
    main()