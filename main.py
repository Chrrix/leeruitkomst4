import tkinter as tk 
from tkinter import ttk
from courseData import SUBJECTS_DATA, QUESTIONS_DATA

# Frame voor de onderwerpen lijst (links)
class SubjectsFrame(ttk.Frame):
    def __init__(self, parent, on_subject_select):
        super().__init__(parent)
        # Maak een listbox voor alle onderwerpen
        self.subjects_list = tk.Listbox(self)
        self.subjects_list.pack(expand=True, fill="both", padx=5, pady=5)
        self.voeg_subjects_toe()
        # Bind de on_subject_select functie
        self.subjects_list.bind('<<ListboxSelect>>', on_subject_select) #used event=None in the function instead of lambda event: on_subject_select(event)

    # Vul de lijst met onderwerpen en examens
    def voeg_subjects_toe(self):
        self.subjects_list.insert(tk.END, "  🚗 ONDERDELEN:") # titel
        for subject in SUBJECTS_DATA["Onderdelen"]:
            self.subjects_list.insert(tk.END, "    " + subject) # extra spaties voor leesbaarheid
        
        # Voeg wat witruimte toe tussen onderdelen en examens
        self.subjects_list.insert(tk.END, "")
        self.subjects_list.insert(tk.END, "")
        
        # Voeg daarna de examens toe
        self.subjects_list.insert(tk.END, "  📝 EXAMEN:")
        for exam in SUBJECTS_DATA["Examen"]:
            self.subjects_list.insert(tk.END, "    " + exam)

    # Haal het geselecteerde item op en verwijder de emoji's
    def get_selected_subject(self):
        selection = self.subjects_list.curselection()
        if not selection:
            return None
        selected_item = self.subjects_list.get(selection[0])
        return selected_item.strip().replace("🚗", "").replace("📝", "")
    

# Frame voor de vragen lijst (midden)
class QuestionsFrame(ttk.Frame):
    def __init__(self, parent, on_question_select):
        super().__init__(parent)
        self.questions_data = {}  # Store the full question data
        self.questions_list = tk.Listbox(self)
        self.questions_list.pack(expand=True, fill="both", padx=5, pady=5)
        self.questions_list.bind('<<ListboxSelect>>', on_question_select)

    # Update de vragenlijst wanneer een nieuw onderwerp wordt geselecteerd
    def update_questions(self, subject):
        self.questions_list.delete(0, tk.END)
        self.questions_data = {}  # Reset stored data
        if subject in QUESTIONS_DATA:
            for i, question in enumerate(QUESTIONS_DATA[subject]):
                self.questions_list.insert(tk.END, question['question'])
                self.questions_data[question['question']] = question  # Store full data
    
    def get_selected_question_data(self):
        selection = self.questions_list.curselection()
        if not selection:
            return None
        selected_question = self.questions_list.get(selection[0])
        return self.questions_data.get(selected_question)

# Frame voor de details van een vraag (rechts)
class DetailsFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.configure(padding="10")
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        
        # Define field configurations - only specify UI-specific properties
        self.field_data = [
            {"name": "type", "label": "Type:", "height": 1},
            {"name": "question", "label": "Vraag:", "height": 3},
            {"name": "options", "label": "Opties:", "height": 6},
            {"name": "correct", "label": "Antwoord:", "height": 1}, 
            {"name": "explanation", "label": "Uitleg:", "height": 4}
        ]
        
        self.create_form_fields()
    
    def create_form_fields(self):
        self.text_widgets = {}
        
        for row, field in enumerate(self.field_data):
            # Create label
            label = ttk.Label(self, text=field["label"])
            label.grid(row=row, column=0, padx=(0,10), pady=(0,10), sticky='nw')
            
            # Create text widget
            text_widget = tk.Text(self, wrap=tk.WORD, height=field["height"])
            text_widget.grid(row=row, column=1, columnspan=3, padx=(0,10), pady=(0,10), sticky='nsew')
            
            # Store reference to text widget
            self.text_widgets[field["name"]] = text_widget

    def update_details(self, question_data):
        if question_data:
            # Clear existing content
            for widget in self.text_widgets.values():
                widget.delete('1.0', tk.END)
            
            for widget in self.text_widgets:
                if widget in question_data:
                    self.text_widgets[widget].insert('1.0', question_data[widget])

# Hoofdapplicatie class
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Theorio vragenbeheer")
        self.geometry("1000x800")
        self.setup_grid()
        self.create_frames()

    # Configureer het grid systeem voor de layout
    def setup_grid(self):
        # Verdeel het scherm in drie kolommen
        self.grid_columnconfigure(0, weight=1)  # Onderwerpen (links)
        self.grid_columnconfigure(1, weight=1)  # Vragen (midden)
        self.grid_columnconfigure(2, weight=2)  # Details (rechts, meer ruimte)
        self.grid_rowconfigure(0, weight=1)

    # Maak en positioneer de verschillende frames
    def create_frames(self):
        # Initialiseer de drie hoofdframes
        self.subjects_frame = SubjectsFrame(self, self.on_subject_select)
        self.questions_frame = QuestionsFrame(self, self.on_question_select)
        self.details_frame = DetailsFrame(self)

        # Positioneer de frames in het grid
        self.subjects_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.questions_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.details_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)

    # Event handler voor wanneer een onderwerp wordt geselecteerd
    def on_subject_select(self, event=None):
        selected_item = self.subjects_frame.get_selected_subject()
        if selected_item:
            self.questions_frame.update_questions(selected_item)
    
    # Event handler voor wanneer een vraag wordt geselecteerd
    def on_question_select(self, event=None):
        question_data = self.questions_frame.get_selected_question_data()
        if question_data:
            self.details_frame.update_details(question_data)

# Start de applicatie
def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
