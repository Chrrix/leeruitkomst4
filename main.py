import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

class NavigatieBalk(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.configure(bg='white')
        self.pack(fill='x', padx=10, pady=10)

        # Knoppen
        self.button = ttk.Button(self, text="📘 Onderdelen")
        self.button.pack(side='left', padx=5, pady=10)

        self.button2 = ttk.Button(self, text="📝 Examens")
        self.button2.pack(side='left', padx=5, pady=10)

        self.button3 = ttk.Button(self, text="📊 Rapporten")
        self.button3.pack(side='left', padx=5, pady=10)

        self.button4 = ttk.Button(self, text="💬 Feedback")
        self.button4.pack(side='left', padx=5, pady=10)

        #Logo
        logo = Image.open("logo.png")
        logo = logo.convert("RGBA")
        resized_logo = logo.resize((128, 56))
        self.logo = ImageTk.PhotoImage(resized_logo)
        self.logo_label = tk.Label(self, image=self.logo, bg='white')
        self.logo_label.pack(side='right')
     
class LijstFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.configure(bg='white')
        self.pack(fill='both', side='left', padx=10, pady=10, expand=True)

        # Lijst
        self.lijst = tk.Listbox(self)
        self.lijst.pack(fill='y', side='left', expand=True)

        # Test
        self.lijst.insert(tk.END, "Onderdeel 1")
        self.lijst.insert(tk.END, "Onderdeel 2")
        self.lijst.insert(tk.END, "Onderdeel 3")

class DetailsFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.configure(bg='white')
        self.pack(fill='both', side='right', padx=10, pady=10, expand=True)

        # Details
        self.details = tk.Text(self)
        self.details.pack(fill='both', expand=True)

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("My App")
        self.root.geometry("800x600")
        self.root.configure(bg='#3374FF')
        
        # Navigatie balk
        self.nav_frame = NavigatieBalk(self.root)

        # Hoofdframe
        self.frame = tk.Frame(self.root, bg='#3374FF')
        self.frame.pack(fill='both', expand=True)
        
        # Linker frame (Lijst)
        self.lijst_frame = LijstFrame(self.frame)
        
        # Rechter frame (Details)
        self.details_frame = DetailsFrame(self.frame)
        # self.right_frame = tk.Frame(self.frame, bg='white')
        # self.right_frame.pack(side='right', fill='both', expand=True, padx=10, pady=10)
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = App()
    app.run()