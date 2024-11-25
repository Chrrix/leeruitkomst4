import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import asyncio
import threading
import aiohttp
from dotenv import load_dotenv
import os
import io
from tkinter import messagebox
import json
from datetime import datetime

# Configuratie voor de API
API_CONFIG = {
    'ENDPOINTS': {
        'subjects': '/http-getAllSubjects',
        'exams': '/http-getAllExams',
        'feedback': '/http-getAllFeedback',
        'update_feedback': '/http-updateFeedbackStatus',
        'create_question': '/http-createQuestion',
        'update_question': '/http-updateQuestion',
        'delete_question': '/http-deleteQuestion',
        'helloWorld': '/helloWorld'
    }
}

# Vraag types voor de popup menu
QUESTION_TYPES = [
    {
        'id': 'multiple_choice',
        'title': 'Multiple Choice',
        'description': 'Een vraag met meerdere antwoordopties waarvan er één correct is.',
        'icon': '📝'
    },
    {
        'id': 'open',
        'title': 'Open Vraag',
        'description': 'Een vraag waar de student een eigen antwoord moet formuleren.',
        'icon': '️✏️'
    },
    {
        'id': 'image_selection',
        'title': 'Afbeelding Selectie',
        'description': 'Een vraag waarbij de student de juiste afbeelding moet selecteren.',
        'icon': '🖼️'
    },
    {
        'id': 'drag_and_drop',
        'title': 'Drag and Drop',
        'description': 'Een vraag waarbij de student items naar de juiste positie moet slepen.',
        'icon': '🎯'
    }
]

def format_date(timestamp):
    """Maak een leesbare datum van een timestamp"""
    if isinstance(timestamp, dict) and '_seconds' in timestamp:
        return datetime.fromtimestamp(timestamp['_seconds']).strftime('%d-%m-%Y %H:%M')
    return ''

class NavigatieBalk(tk.Frame):
    """Navigation bar met knoppen en logo"""
    
    def __init__(self, parent, app):
        super().__init__(parent)
        self.pack(fill='x', padx=10, pady=10)
        self.create_nav_buttons(app)
        self.add_logo()
    
    def create_nav_buttons(self, app):
        """Maak de knoppen voor de navigatie"""
        buttons = [
            # Sommige knoppen hebben een lambda functie om de async functie aan te roepen, deze zijn async omdat ze data ophalen van de API en dan pas de UI updaten
            ("📘 Onderdelen", lambda: app.handle_async_button(app.show_onderdelen())),
            ("📝 Examens", lambda: app.handle_async_button(app.show_exams())),
            ("📊 Rapporten", app.show_rapporten),
            ("💬 Feedback", lambda: app.handle_async_button(app.show_feedback()))
        ]
        
        for text, command in buttons:
            btn = ttk.Button(self, text=text, command=command)
            btn.pack(side="left", padx=5, pady=10)
    
    def add_logo(self):
        """Aan de rechterkant van de navigatiebalk een logo"""
        try:
            logo = Image.open("logo.png")
            logo = logo.convert("RGBA")
            resized_logo = logo.resize((128, 56))
            self.logo = ImageTk.PhotoImage(resized_logo)
            self.logo_label = tk.Label(self, image=self.logo)
            self.logo_label.pack(side="right")
        except Exception as e:
            print("Error bij het laden van het logo: ", e)

class LijstFrame(tk.Frame):
    """De lijstframe is de linker frame die de lijst met onderdelen, examens en feedback toont"""
    #! Setup
    def __init__(self, parent, app):
        super().__init__(parent)
        self.pack(fill='both', side='left', padx=10, pady=10, expand=False)
        self.configure(width=300)
        self.pack_propagate(False) #Zorgt ervoor dat de lijstframe niet groter wordt dan de inhoud
        self.app = app
        self.vraag_data = {} #Dit is een dictionary die de data van de vragen opslaat zodat deze gemakkelijk kunnen worden opgehaald in de on_select functie
        self.feedback_data = {} #Zelfde als hierboven, maar voor de feedback data

        self.container = tk.Frame(self)
        self.container.pack(fill='both', expand=True)

        # Loading label
        self.loading_label = tk.Label(
            self.container,
            text="🔄 Ophalen van data...",
            font=('Arial', 12),
            pady=20
        )

        # Style voor de Treeview
        style = ttk.Style()
        style.configure("Custom.Treeview", rowheight=40)
        style.configure("Custom.Treeview.Item", padding=5)

        # Treeview
        self.tree = ttk.Treeview(self.container, style="Custom.Treeview")
        self.tree.pack(fill='both', expand=True)
        
        # Popup menu, voor het maken van nieuwe vragen
        self.popup_menu = tk.Menu(self, tearoff=0)
        self.popup_menu.add_command(label="+ Maak vraag", command=self.create_new_question)
        
        # Wanneer er op een item in de treeview wordt geklikt, roepen we de on_select functie aan
        self.tree.bind('<<TreeviewSelect>>', self.on_select)

    #! Update functies
    def update_lijst(self, items, loading=True):
        """Update de lijst met items, en toon de loading label als loading=True, check ook wat voor soort items er zijn"""
        if loading:
            self.tree.pack_forget() #Verberg de treeview
            self.loading_label.pack(fill='both', expand=True)
            self.update()
            return

        self.loading_label.pack_forget() #Verberg de loading label
        self.tree.pack(fill='both', expand=True) #Toon de treeview
        
        #Verwijder alle items uit de vraag_data dictionary
        self.vraag_data.clear()
        self.feedback_data.clear()
        for item in self.tree.get_children(): #Verwijder alle items uit de treeview
            self.tree.delete(item)
            
        # Voeg de nieuwe items toe aan de treeview
        for item in items:
            #de meest omslachtige check, maar het werkt en had echt geen tijd meer om er een betere te maken
            if isinstance(item, list) and all(isinstance(x, dict) and 'feedback' in x for x in item): #Feedback lijst
                # This is the feedback list
                for feedback in item:
                    unique_id = f"feedback-{feedback['id']}" #Maak een unieke id voor de feedback, anders vind de treeview deze niet leuk, ook kunnen wea dan kijken bij on_select of het feedback is
                    self.feedback_data[unique_id] = feedback #sla de feedback op in de feedback_data dictionary
                    
                    # Leuke emoji's voor de status
                    status_emoji = {
                        'in_progress': '🔄',
                        'completed': '✅',
                        'pending': '⏳'
                    }.get(feedback.get('status', 'new'), '🆕')
                    
                    # Format de datum
                    date_str = format_date(feedback.get('date', {}))
                    
                    # Maak de display text
                    display_text = f"{status_emoji} {date_str} - {feedback.get('subject', 'Geen onderwerp')}"
                    
                    self.tree.insert("", "end", iid=unique_id, text=display_text)
            
            # Onderdelen en examens zijn dictionaries met een titel en een lijst van vragen
            elif isinstance(item, dict): 
                parent = self.tree.insert("", "end", text=item['titel'])
                
                # Voeg de knop "[+ Nieuwe vraag toevoegen]" toe aan het hoofdstuk
                self.tree.insert(parent, "end", 
                               text="+ Nieuwe vraag toevoegen", 
                               tags=('add_button',), #Hierdoor kunnen wij in on_select vinden wat er is geklikt
                               values=(parent,)) #Values zijn voor extra informatie, zodat we later de parent kunnen vinden
                
                # Voeg de vragen toe aan het hoofdstuk
                for vraag in item['vragen']:
                    unique_id = item['titel']+'-'+vraag['id']+'-'+vraag['titel'] #Maak een unieke id voor de vraag, anders vind de treeview deze niet leuk
                    self.vraag_data[unique_id] = vraag #Sla de vraag op in de vraag_data dictionary
                    self.tree.insert(parent, "end", iid=unique_id, text=vraag['vraag_tekst'])
            else: #Rapporten zijn strings (maar dit is ook niet future proof, want ik wil het later meer rapporten toevoegen)
                self.tree.insert("", "end", text=str(item))
            
            #In de toekomst zou ik deze functie willen herschrijven zodat het meer flexibel is, met eventueel een extra parameter voor het type item (onderdeel, examen, feedback, rapport) 🤷‍♂️

    def create_new_question(self):
        """Maak een nieuwe vraag aan"""
        if hasattr(self, 'selected_parent'):
            parent_text = self.tree.item(self.selected_parent)['text']
            
            # Laat de gebruiker een type kiezen in een popup modal
            dialog = QuestionTypeDialog(self)
            self.wait_window(dialog) #Wacht tot de gebruiker een type heeft gekozen
            
            # Als er een type is gekozen
            if dialog.result:
                # Maak een lege vraag template
                empty_question = {
                    'id': 'new',
                    'titel': 'Nieuwe vraag',
                    'vraag_tekst': '',
                    'type': dialog.result,
                    'opties': [],
                    'antwoord': '',
                    'uitleg': '',
                    'afbeelding': '',
                    'context': '',
                    'terms': {},
                    'imageOptions': [],
                    'correctPositions': [],
                    'parent': parent_text
                }
                
                # Toon de vraag details met de lege template
                self.app.show_vraag_details(parent_text, empty_question)

    def on_select(self, event):
        """Wanneer er op een item in de treeview wordt geklikt, roepen we deze functie aan, er kunnen 4 dingen gebeuren:
        1. Er is op de knop "[+ Nieuwe vraag toevoegen]" geklikt, dan maken we een nieuwe vraag aan
        2. Er is op een vraag geklikt, dan tonen we de vraag details
        3. Er is op een feedback item geklikt, dan tonen we de feedback details
        4. Er is op een rapport geklikt, dan tonen we de rapport details (Voor nu altijd de feedback rapporten)"""
        selection = self.tree.selection()
        if not selection: #Als er niks is geselecteerd, stop
            return
        
        selected_item = selection[0] #Pak het eerste item, want we doen niet aan meerdere selectie
        selected_text = self.tree.item(selected_item)['text']
        
        # Er is op de knop "Export feedback" geklikt, dan tonen we de feedback rapport details
        if selected_text == "Export feedback":
            self.app.handle_async_button(self.app.show_rapport_feedback_details())
            return

        print(f"Selected item: {selected_item}")
        # Er is op een feedback item geklikt, dan tonen we de feedback details
        if selected_item.startswith('feedback-'):
            feedback_data = self.feedback_data.get(selected_item)
            print(f"Feedback data: {feedback_data}")
            if feedback_data:
                self.app.show_feedback_details(feedback_data)
            return
        
        # Er is op de knop "[+ Nieuwe vraag toevoegen]" geklikt, dan maken we een nieuwe vraag aan
        if 'add_button' in self.tree.item(selected_item)['tags']:
            # Get parent from values
            parent_id = self.tree.item(selected_item)['values'][0]
            parent_text = self.tree.item(parent_id)['text']
            self.selected_parent = parent_id
            self.create_new_question()
            return
        
        # Er is op een vraag geklikt, dan tonen we de vraag details
        parent_id = self.tree.parent(selected_item)
        
        if parent_id:  # Dit is een vraag, want er is een parent dus examen of onderdeel, dit is niet future proof want stel we maken later andere items met dropdowns dan moet dit worden aangepast
            vraag_data = self.vraag_data.get(selected_item)
            if vraag_data:
                parent_text = self.tree.item(parent_id)['text']
                self.app.show_vraag_details(
                    hoofdstuk=parent_text,
                    vraag_data=vraag_data
                )

class DetailsFrame(tk.Frame):
    """De details frame is de rechter frame die de details van een vraag, feedback of rapport toont; De belangrijkste functies zijn show_vraag_ui, show_feedback_ui en show_rapport_feedback_ui, als het rest zijn onderdelen hiervan"""
    def __init__(self, parent, app):
        #! Setup
        super().__init__(parent)
        self.pack(fill='both', side='right', padx=10, pady=10, expand=True)
        self.app = app
        
        self.content_frame = tk.Frame(self)
        self.content_frame.pack(fill='both', expand=True)

        # Bewaar de geladen afbeeldingen om garbage collection te voorkomen
        self.loaded_images = []

    # laad url images met TKinter
    async def load_image_from_url(self, url, size=(100, 100)):
        """Laad een afbeelding van een URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        # Read image data
                        image_data = await response.read()
                        # Convert to PIL Image
                        image = Image.open(io.BytesIO(image_data))
                        # Resize image
                        image = image.resize(size, Image.Resampling.LANCZOS)
                        # Convert to PhotoImage
                        photo = ImageTk.PhotoImage(image)
                        return photo
        except Exception as e:
            print(f"Fout bij het laden van de afbeelding {url}: {e}")
            return None

    def show_vraag_ui(self, hoofdstuk, vraag_data):
        """Dit is de UI die wordt getoond wanneer er op een vraag wordt geklikt, het past zicht aan op basis van het type vraag"""
        # Initialize all possible storage variables
        self.terms_entries = [] #Opslag voor de begrippen (terms)
        self.position_frames = [] #Opslag voor de positie frames (drag and drop)
        self.option_entries = []  # Opslag voor de antwoord opties (multiple choice)
        self.selected_option = None  # Opslag voor de geselecteerde optie (multiple choice), default is None want er is nog geen optie geselecteerd
        self.image_urls = [] #Opslag voor de afbeeldingen (image selection)
        self.current_type = vraag_data['type'] #Opslag voor het type vraag
        self.image_url = vraag_data.get('image', '') #Opslag voor de afbeelding (image selection)
        self.parent = hoofdstuk  # Opslag voor de parent/hoofdstuk

        # Maak de UI leeg
        self.clear_content()
        
        # Maak de hoofd container
        main_container = self.create_scrollable_frame(self.content_frame)
        self.create_header(main_container, hoofdstuk, vraag_data)
        content_container = self.create_content_container(main_container)

        # Maak de linker en rechter kolom   
        left_column = self.create_left_column(content_container)
        self.create_right_column(content_container, vraag_data)
        
        # Maak de context, vraag, begrippen, antwoord en feedback secties
        self.create_question_context(left_column, vraag_data)
        self.create_question_frame(left_column, vraag_data)
        self.create_terms_frame(left_column, vraag_data)
        self.create_answer_and_options_frame(left_column, vraag_data)
        self.create_feedback_section(main_container, vraag_data)
        self.create_positions_section(main_container, vraag_data)

    def create_scrollable_frame(self, parent):
        """Maak een scrollbare container, voor show_vraag_ui"""
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)

        canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')

        def configure_scroll_region(event): # Alles is scrollbaar
            canvas.configure(scrollregion=canvas.bbox('all'))

        scrollable_frame.bind('<Configure>', configure_scroll_region)
        return scrollable_frame

    def create_header(self, parent, hoofdstuk, vraag_data):
        """Maak de header van de vraag, hier staat de titel en de knoppen voor verwijderen en opslaan, voor show_vraag_ui"""
        header_frame = tk.Frame(parent, padx=20, pady=10)
        header_frame.pack(fill='x')

        header_left = tk.Frame(header_frame)
        header_left.pack(side='left')

        header_right = tk.Frame(header_frame)
        header_right.pack(side='right')

        # Voeg de titel toe
        tk.Label(header_left, text=f"📘 {hoofdstuk} - {vraag_data['id']}", font=('Arial', 16, 'bold'),).pack(anchor='w')

        # Voeg de knop "Verwijderen" toe
        ttk.Button(header_right, text="Verwijderen", style='Accent.TButton', width=20, command=lambda: self.delete_question(vraag_data['id'])).pack(side='right', padx=(5, 0), pady=5)

        ttk.Button(header_right, text="Opslaan", style='Accent.TButton', width=20, command=lambda: self.save_question(vraag_data['id'])).pack(side='right', pady=5)

    def save_question(self, question_id):
        """Deze functie slaat de vraag op in de API, zowel voor nieuwe als voor bestaande vragen, gebruikt in show_vraag_ui"""
        question_data = {
            'type': self.current_type,
            'parent': self.parent  # Use the stored parent value
        }

        # Haal de tekst uit de tekst widgets veilig op
        def safe_get_text(widget):
            try:
                if widget and widget.winfo_exists():
                    return widget.get('1.0', 'end-1c')
                return ''
            except (tk.TclError, AttributeError):
                return ''

        # Voeg de basis vraag data toe, die alle vraag types gemeen hebben
        try:
            question_data['question'] = safe_get_text(self.question_text)
            question_data['explanation'] = safe_get_text(self.explanation_text)
        except Exception as e:
            print(f"Error getting basic question data: {e}")
            messagebox.showerror("Error", "Failed to save question text or explanation")
            return

        # Check welke vraagtype het is en voeg de bijbehorende data toe
        try:
            if self.current_type == 'multiple_choice':
                answers = []
                for opt in getattr(self, 'option_entries', []):
                    try:
                        answers.append(opt.get())
                    except tk.TclError:
                        continue
                
                question_data.update({
                    'answers': answers,
                    'correctAnswer': self.answer_entry.get() if hasattr(self, 'answer_entry') else ''
                })

            elif self.current_type == 'image_selection':
                if hasattr(self, 'image_entries'):  # Nieuwe vragen hebben image_entries
                    print("self.image_entries", self.image_entries)
                    image_urls = [entry.get() for entry in self.image_entries]
                    question_data.update({
                        'imageOptions': image_urls,
                        'correctAnswer': int(self.answer_entry.get()) if hasattr(self, 'answer_entry') else 0
                    })
                else:
                    question_data.update({
                        'imageOptions': getattr(self, 'image_urls', []),
                    'correctAnswer': int(self.answer_entry.get()) if hasattr(self, 'answer_entry') else 0
                })

            elif self.current_type == 'drag_and_drop':
                positions = []
                for pos_frame in getattr(self, 'position_frames', []):
                    try:
                        positions.append({
                            'positionX': float(pos_frame.x_entry.get()),
                            'positionY': float(pos_frame.y_entry.get())
                        })
                    except (ValueError, tk.TclError):
                        continue
                question_data['correctPositions'] = positions

        except Exception as e:
            print(f"Fout bij het ophalen van de type-specifieke data: {e}")
            messagebox.showerror("Fout", "Fout bij het opslaan van de type-specifieke vraag data")
            return

        # Voeg de optionele velden toe
        try:
            # Check of er een context is
            if hasattr(self, 'context_text'):
                context = safe_get_text(self.context_text)
                if context:
                    question_data['context'] = context

            # Check of er begrippen zijn
            if hasattr(self, 'terms_entries'):
                terms = {}
                for term_frame in self.terms_entries:
                    try:
                        term = term_frame.term_entry.get()
                        definition = term_frame.def_entry.get()
                        if term and definition:
                            terms[term] = definition
                    except tk.TclError:
                        continue #TIJDELIJK! doorgaan bij fout
                if terms:
                    question_data['terms'] = terms

            # Check of er een afbeelding is
            if hasattr(self, 'image_url') and self.image_url: 
                question_data['image'] = self.image_url

        except Exception as e:
            print(f"Fout bij het ophalen van de optionele velden: {e}")
            messagebox.showerror("Fout", "Fout bij het opslaan van de optionele vraag data")
            return

        # Kies of er een vraag wordt aangemaakt of geüpdate, op basis van de question_id
        if question_id == 'new': #Nieuwe vraag hebben altijd een id van 'new', vanwege de template
            self.app.handle_async_button(self.create_question(question_data))
        else:
            question_data['id'] = question_id
            self.app.handle_async_button(self.update_question(question_data))

    async def update_question(self, question_data):
        """Deze functie update een bestaande vraag in de API, triggerd wanneer je op de knop 'Opslaan' drukt in show_vraag_ui"""
        print("Updating question:", question_data)
        try:
            await self.app.api_client.put('update_question', question_data)
            messagebox.showinfo("Success", "Vraag opgeslagen in de database!")
        except Exception as e:
            messagebox.showerror("Error", f"Error updating question: {str(e)}")

    def create_content_container(self, parent):
        """Maak de content container, hier wordt de hoofd container voor de vraag details, voor show_vraag_ui"""
        content_container = tk.Frame(parent, padx=20)
        content_container.pack(fill='both', expand=True)
        return content_container

    def create_left_column(self, parent):
        """Maak de linker kolom, voor show_vraag_ui"""
        left_column = tk.Frame(parent)
        left_column.pack(side='left', fill='both', expand=True, padx=(0, 10))
        return left_column

    def create_right_column(self, parent, vraag_data):
        """Maak de rechter kolom (eigenlijk de afbeelding), voor show_vraag_ui"""
        right_column = tk.Frame(parent)
        right_column.pack(side='right', fill='both', padx=(10, 0))
        if vraag_data.get('afbeelding'):
            self.app.handle_async_button(self.load_and_display_question_image(
                right_column, 
                vraag_data['afbeelding']
            ))
        return right_column

    def create_question_context(self, parent, vraag_data):
        """Maak de context sectie, voor show_vraag_ui"""
        if vraag_data['type'] in ['open', 'multiple_choice']:
            try:
                context_frame = tk.Frame(parent)
                context_frame.pack(fill='x', pady=10)
                
                tk.Label(context_frame, text="Context ({} voor termen en [] voor italic):", font=('Arial', 12, 'bold'),).pack(anchor='w')
                
                self.context_text = tk.Text(context_frame,height=5,font=('Arial', 11),width=30,wrap='word',)
                self.context_text.pack(fill='x', pady=5)
                
                if 'context' in vraag_data:
                    self.context_text.insert('1.0', vraag_data['context'])
            except Exception as e:
                print(f"Error creating context: {e}")
                self.context_text = None

    def create_question_frame(self, parent, vraag_data):
        """Maak de vraag sectie (de daadwerkelijke vraag tekst), voor show_vraag_ui"""
        question_frame = tk.Frame(parent)
        question_frame.pack(fill='x', pady=10)
        
        tk.Label(question_frame,text="Vraag:",font=('Arial', 12, 'bold'),).pack(anchor='w')
        
        self.question_text = tk.Text(question_frame,height=4,font=('Arial', 11),wrap='word',)
        self.question_text.pack(fill='x', pady=5)
        self.question_text.insert('1.0', vraag_data['vraag_tekst'])

    def create_terms_frame(self, parent, vraag_data):
        """Maak de begrippen sectie (begrippen, en + knop om nieuwe begrippen toe te voegen), voor show_vraag_ui"""
        if vraag_data['type'] in ['open', 'multiple_choice']:
            terms_frame = tk.Frame(parent)
            terms_frame.pack(fill='x', pady=(20, 10))
            
            header_frame = tk.Frame(terms_frame)
            header_frame.pack(fill='x', pady=(0, 5))
            
            tk.Label(header_frame,text="Begrippen:",font=('Arial', 12, 'bold'),).pack(side='left')
            
            ttk.Button(header_frame,text="+ Nieuw begrip",style='Accent.TButton',width=15,command=lambda: self.create_term_entry(terms_container)).pack(side='right')
            
            terms_container = tk.Frame(terms_frame)
            terms_container.pack(fill='x')
            
            self.terms_entries = [] #Empty list om de begrippen op te slaan
            for term, definition in vraag_data.get('terms', {}).items():
                self.create_term_entry(terms_container, term, definition)

    def create_term_entry(self, parent, term='', definition=''):
        """Maak een begrip entry, met een term en definitie en een knop om het te verwijderen, voor show_vraag_ui"""
        class TermFrame:  # Helper class om de entry references op te slaan
            def __init__(self, term_entry, def_entry, frame,):
                self.term_entry = term_entry
                self.def_entry = def_entry
                self.frame = frame

        term_frame = tk.Frame(parent)
        term_frame.pack(fill='x', pady=2)
        
        # Maak de linker kolom voor de term
        term_left = tk.Frame(term_frame)
        term_left.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        tk.Label(term_left,text="Term:",font=('Arial', 10, 'bold')).pack(side='left', padx=(0, 5))
        
        term_entry = ttk.Entry(term_left, width=20)
        term_entry.pack(side='left', fill='x', expand=True)
        term_entry.insert(0, term)
        
        # Maak de rechter kolom voor de definitie
        def_right = tk.Frame(term_frame)
        def_right.pack(side='left', fill='x', expand=True, padx=(5, 0))
        
        tk.Label(def_right,text="Definitie:",font=('Arial', 10, 'bold')).pack(side='left', padx=(0, 5))
        
        def_entry = ttk.Entry(def_right)
        def_entry.pack(side='left', fill='x', expand=True)
        def_entry.insert(0, definition)
        
        # Delete knop die de hele entry verwijderd
        ttk.Button(term_frame,text="×",width=3,style='Accent.TButton',
            command=lambda: (
                term_frame.destroy(),
                self.terms_entries.remove(term_obj)
            )
        ).pack(side='right', padx=(5, 0))
        
        term_obj = TermFrame(term_entry, def_entry, term_frame)
        self.terms_entries.append(term_obj) #Voeg de term toe aan de lijst

    def create_answer_and_options_frame(self, parent, vraag_data):
        """Maak de antwoord sectie (antwoord), voor show_vraag_ui"""
        if vraag_data['type'] != 'drag_and_drop': #Drag and drop heeft geen antwoord
            answer_frame = tk.Frame(parent)
            answer_frame.pack(fill='x', pady=10)
            
            tk.Label(answer_frame, text="Antwoord:", font=('Arial', 12, 'bold'),).pack(anchor='w')
            
            if vraag_data['type'] == 'multiple_choice':
                self.create_multiple_choice_ui(answer_frame, vraag_data)
            elif vraag_data['type'] == 'image_selection':
                self.create_image_selection_ui(answer_frame, vraag_data)
            elif vraag_data['type'] == 'open':
                self.create_open_question_ui(answer_frame, vraag_data)
        else:
            #bij drag and drop vraag, geen antwoord maar kan hier wel gebruik maken om ff bij nieuwe vraag een image url te maken
            if vraag_data['id'] == 'new':
                tk.Label(answer_frame,text="Afbeelding URL:",font=('Arial', 10)).pack(side='left', padx=(0, 5))
                self.image_entry = ttk.Entry(answer_frame, width=20, name=f'new_image_option')
                self.image_entry.pack(side='left', padx=(0, 5))

    def create_multiple_choice_ui(self, parent, vraag_data):
        """Maak de multiple choice sectie (opties), voor show_vraag_ui"""
        self.option_entries = []  # Lege lijst om de opties op te slaan
        
        # Maak het frame voor het correcte antwoord
        correct_answer_frame = tk.Frame(parent)
        correct_answer_frame.pack(fill='x', pady=5)
        
        tk.Label(correct_answer_frame, text="Correct antwoord:", font=('Arial', 10)).pack(side='left', padx=(0, 5))
        
        self.answer_entry = ttk.Entry(correct_answer_frame)  # Opslag voor het correcte antwoord
        self.answer_entry.pack(side='left', fill='x', expand=True)
        if 'antwoord' in vraag_data:
            self.answer_entry.insert(0, vraag_data['antwoord'])
        
        # Knop om nieuwe opties toe te voegen
        add_option_frame = tk.Frame(parent)
        add_option_frame.pack(fill='x', pady=5)
        
        ttk.Button(
            add_option_frame,
            text="+ Nieuwe optie",
            style='Accent.TButton',
            command=lambda: self.add_multiple_choice_option()
        ).pack(side='right')

        # Container voor de opties
        self.options_container = tk.Frame(parent)
        self.options_container.pack(fill='x')

        # Voeg de bestaande opties toe
        for optie in vraag_data.get('opties', []):
            self.add_multiple_choice_option(optie)

        #Alleen bij het maken van nieuwe vragen, geef de urls op van de imageOptions
        if vraag_data['id'] == 'new':
            print("Nieuwe vraag, maak image entry")
            tk.Label(correct_answer_frame,text="Afbeelding URL:",font=('Arial', 10)).pack(side='left', padx=(0, 5))
            self.image_entry = ttk.Entry(correct_answer_frame, width=20, name=f'new_image_option')
            self.image_entry.pack(side='left', padx=(0, 5))

    def add_multiple_choice_option(self, value=''):
        """Voeg een optie toe aan de multiple choice sectie, voor create_multiple_choice_ui"""
        option_frame = tk.Frame(self.options_container)
        option_frame.pack(fill='x', pady=2)
    
        option_var = tk.StringVar(value=value) #StringVar reageert op veranderingen en moet dus voor de entry staan
        self.option_entries.append(option_var)
        
        # Create the option entry
        entry = ttk.Entry(
            option_frame,
            textvariable=option_var,
        )
        entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        # Knop om de optie te verwijderen
        ttk.Button(option_frame,text="×",width=3,style='Accent.TButton',
            command=lambda: (
                option_frame.destroy(),
                self.option_entries.remove(option_var)
            )
        ).pack(side='left', padx=(5, 0))


    def create_image_selection_ui(self, parent, vraag_data):
        """Maak de image selection sectie (opties), voor show_vraag_ui"""
        images_frame = tk.Frame(parent)
        images_frame.pack(fill='x', pady=5)
        
        answer_container = tk.Frame(parent)
        answer_container.pack(fill='x', pady=5)
        
        tk.Label(answer_container,text="Antwoord (0-3):",font=('Arial', 10)).pack(side='left', padx=(0, 5)) #de user moet het antwoord invullen (mogelij moet er input validatie komen)
        
        self.answer_entry = ttk.Entry(answer_container, width=5)  # Opslag voor het correcte antwoord
        self.answer_entry.pack(side='left')
        if 'correctAnswer' in vraag_data:
            self.answer_entry.insert(0, str(vraag_data['correctAnswer']))
        
        self.image_urls = vraag_data['imageOptions']  # Opslag voor de afbeeldingen
        
        # Maak de afbeeldingen in een grid van 2x2
        for i, image_url in enumerate(self.image_urls, 1):
            row = (i-1) // 2
            col = (i-1) % 2
            option_frame = tk.Frame(images_frame)
            option_frame.grid(row=row, column=col, padx=5, pady=5)
            #Laad de afbeeldingen asynchroon, zodat deze niet in de weg staan bij het maken van de grid
            self.app.handle_async_button(self.load_and_display_option_image(option_frame, image_url, i))

        #Alleen bij het maken van nieuwe vragen, geef de urls op van de imageOptions
        if vraag_data['id'] == 'new':
            print("Nieuwe vraag, maak image entries")
            tk.Label(images_frame,text="Afbeeldingen URLS:",font=('Arial', 10, 'bold')).pack(side='left', padx=(0, 5))
            self.image_entries = []
            for i in range(4):
                entry = ttk.Entry(images_frame, width=20, name=f'new_image_option_{i}')
                entry.pack(side='left', padx=(0, 5))
                self.image_entries.append(entry)


    def create_open_question_ui(self, parent, vraag_data):
        """Maak de open vraag antwoord sectie, voor show_vraag_ui"""
        antwoord_text = tk.Text(
            parent,
            height=4,
            font=('Arial', 11),
            wrap='word',
            width=30
        )
        antwoord_text.pack(fill='x', pady=5)
        if 'antwoord' in vraag_data:
            antwoord_text.insert('1.0', vraag_data['antwoord'])

    def create_feedback_section(self, parent, vraag_data):
        """Maak de feedback sectie (uitleg), voor show_vraag_ui"""
        uitleg_frame = tk.Frame(parent, padx=20)
        uitleg_frame.pack(fill='x', pady=10)
        
        tk.Label(
            uitleg_frame,
            text="Uitleg:",
            font=('Arial', 12, 'bold'),
        ).pack(anchor='w')
        
        self.explanation_text = tk.Text(uitleg_frame,height=3,font=('Arial', 11),wrap='word',width=30)
        self.explanation_text.pack(fill='x', pady=5)
        if 'uitleg' in vraag_data:
            self.explanation_text.insert('1.0', vraag_data['uitleg'])

    def create_positions_section(self, parent, vraag_data):
        """Maak de positie sectie bij drag and drop vragen, voor show_vraag_ui"""
        if vraag_data['type'] == 'drag_and_drop':
            positions_frame = tk.Frame(parent, padx=20)
            positions_frame.pack(fill='x', pady=10)
            
            positions_header = tk.Frame(positions_frame)
            positions_header.pack(fill='x', pady=(0, 5))
            
            tk.Label(positions_header,text="Posities:",font=('Arial', 12, 'bold'),).pack(side='left')
            
            positions_container = tk.Frame(positions_frame)
            positions_container.pack(fill='x')
            
            self.position_frames = []  # Lege lijst om de positie frames op te slaan
            
            ttk.Button(positions_header,text="+ Nieuwe positie",style='Accent.TButton',width=15,
                command=lambda: self.add_position_entry(positions_container)
            ).pack(side='right')
            
            for i, pos in enumerate(vraag_data.get('correctPositions', [])):
                self.add_position_entry(
                    positions_container,
                    index=i,
                    x=pos.get('positionX', 0),
                    y=pos.get('positionY', 0)
                )

    def add_position_entry(self, container, index=None, x=0, y=0):
        """Voeg een positie toe aan de drag and drop sectie, voor create_positions_section (eigenlijk zelfde als create_term_entry)"""
        class PositionFrame:  # Helper class to store entry references
            def __init__(self, x_entry, y_entry):
                self.x_entry = x_entry
                self.y_entry = y_entry

        position_frame = tk.Frame(container)
        position_frame.pack(fill='x', pady=2)
        
        tk.Label(
            position_frame,
            text=f"Positie {index + 1 if index is not None else len(self.position_frames) + 1}:", 
            # Bij bestaande posities: gebruikt index + 1
            # Bij nieuwe positie: gebruikt len(self.position_frames) + 1 omdat index None is
            font=('Arial', 10, 'bold')
        ).pack(side='left', padx=(0, 10))
        
        tk.Label(position_frame,text="X:",font=('Arial', 10)).pack(side='left', padx=(0, 5))
        
        x_entry = ttk.Entry(position_frame, width=8)
        x_entry.pack(side='left', padx=(0, 10))
        x_entry.insert(0, str(x))
        
        tk.Label(position_frame,text="Y:",font=('Arial', 10)).pack(side='left', padx=(0, 5))
        
        y_entry = ttk.Entry(position_frame, width=8)
        y_entry.pack(side='left')
        y_entry.insert(0, str(y))
        
        pos_obj = PositionFrame(x_entry, y_entry)
        self.position_frames.append(pos_obj)
        
        ttk.Button(position_frame,text="×",width=3,style='Accent.TButton',
        command=lambda: (
                position_frame.destroy(),
                self.position_frames.remove(pos_obj)
            )
        ).pack(side='right', padx=(10, 0))
        
        ttk.Separator(container).pack(fill='x', pady=5)

    async def load_and_display_question_image(self, container, image_url):
        """Laad en display de vraag afbeelding, voor de rechter kolom bij show_vraag_ui (open vraag, multiple choice)"""
        photo = await self.load_image_from_url(image_url, size=(200, 200))
        if photo:
            self.loaded_images.append(photo)
            img_frame = tk.Frame(container, relief='solid')
            img_frame.pack(pady=10)
            
            img_label = tk.Label(img_frame, image=photo)
            img_label.pack(padx=10, pady=10)

    async def load_and_display_option_image(self, container, image_url, option_num):
        """Laad en display de afbeelding bij image selection vragen, voor create_image_selection_ui"""
        photo = await self.load_image_from_url(image_url, size=(100, 100))
        if photo:
            self.loaded_images.append(photo)
            
            # Label met afbeelding
            img_label = tk.Label(
                container,
                image=photo
            )
            img_label.pack(padx=5, pady=5)
            
            # Label met optie nummer
            tk.Label(
                container,
                text=f"Optie {option_num-1}",
                font=('Arial', 10)
            ).pack()

    def show_feedback_ui(self, feedback_data):
        """Maak de feedback view, voor show_feedback"""
        self.clear_content() #Verwijder alle widgets in content_frame
        main_container = self.create_scrollable_frame(self.content_frame)
        
        # Header met de titel
        header_frame = tk.Frame(main_container, padx=20, pady=10)
        header_frame.pack(fill='x')
        
        tk.Label(header_frame, text=f"Feedback: {feedback_data.get('subject', '')}", font=('Arial', 16, 'bold')).pack(side='left')
        
        # Frame voor status controls
        status_controls_frame = tk.Frame(main_container, padx=20, pady=10)
        status_controls_frame.pack(fill='x')
        
        # Status label en dropdown aan de linkerkant
        status_left_frame = tk.Frame(status_controls_frame)
        status_left_frame.pack(side='left')
        
        tk.Label(status_left_frame,text="Status:",font=('Arial', 12, 'bold')).pack(side='left', padx=(0, 10))
        
        status_var = tk.StringVar(value=feedback_data.get('status', 'pending'))
        status_dropdown = ttk.Combobox(status_left_frame,textvariable=status_var,values=['pending', 'in_progress', 'completed'],width=20)
        status_dropdown.pack(side='left')
        
        # Opslaan knop
        ttk.Button(status_controls_frame,text="Opslaan",style='Accent.TButton',
            command=lambda: self.app.handle_async_button(
                self.update_feedback_status(
                    feedback_data['id'], 
                    status_var.get()
                )
            )
        ).pack(side='right')
        
        # Vraag ID sectie
        if feedback_data.get('questionId'):
            question_id_frame = tk.Frame(main_container, padx=20, pady=10)
            question_id_frame.pack(fill='x')
            
            tk.Label(question_id_frame,text="Vraag ID:",font=('Arial', 12, 'bold')).pack(side='left', padx=(0, 10))
            
            tk.Label(question_id_frame,text=feedback_data['questionId'],font=('Arial', 12)).pack(side='left')

        # Datum
        if 'date' in feedback_data:
            date_str = format_date(feedback_data['date'])
            tk.Label(
                status_controls_frame,
                text=f"Datum: {date_str}",
                font=('Arial', 12)
            ).pack(side='right')
        
        # Laat zien welke gebruiker feedback heeft gegeven
        if feedback_data.get('userId'):
            user_frame = tk.Frame(main_container, padx=20, pady=10)
            user_frame.pack(fill='x')
            
            tk.Label(user_frame, text=f"Gebruiker ID: {feedback_data['userId']}", font=('Arial', 12)).pack(anchor='w')
        
        # Feedback content
        content_frame = tk.Frame(main_container, padx=20, pady=10)
        content_frame.pack(fill='both', expand=True)
        
        tk.Label(content_frame, text="Feedback:",font=('Arial', 12, 'bold')).pack(anchor='w')
        
        feedback_text = tk.Text(content_frame, height=10, font=('Arial', 11), wrap='word')
        feedback_text.pack(fill='both', expand=True, pady=5)
        feedback_text.insert('1.0', feedback_data.get('feedback', ''))
        feedback_text.config(state='disabled')

    def clear_content(self):
        """Verwijder alle widgets in content_frame"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def delete_question(self, question_id):
        """Verwijder een vraag voor perongeluke verwideren voorkomen, voor show_onderdelen_ui"""
        if messagebox.askyesno("Bevestiging", "Weet je zeker dat je deze vraag wilt verwijderen?"):
            self.app.handle_async_button(self.delete_question_request(question_id))

    async def delete_question_request(self, question_id):
        """Verwijder een vraag, voor delete_question"""
        try:
            await self.app.api_client.delete('delete_question', {'id': question_id})
            messagebox.showinfo("Success", "Vraag succesvol verwijderd!")
            # Refresh de lijst
            await self.app.show_onderdelen()
        except Exception as e:
            messagebox.showerror("Error", f"Fout bij verwijderen van vraag: {str(e)}")

    async def create_question(self, question_data):
        """Maak een vraag, wanneer iemand op opslaat drukt en de id is 'new' (dus niet bestaat in de database)"""
        print("create_question: ", question_data)
        required_fields = ['question', 'type'] # VULT DIT AAN
        missing_fields = [field for field in required_fields if not question_data.get(field)]
        
        if missing_fields:
            messagebox.showerror("Error", f"Vul de volgende velden in: {', '.join(missing_fields)}")
            return False

        # Helaas moeten we hier weer terug de data formatteren naar de verwachtingen van de cloud functie/firestore database
        # Ook hoeven we niet alle question_data velden mee te geven uit de lege template die we krijgen van de cloud functie
        # Dit kan denk ik efficiënter, maar het werkt nu wel
        formatted_data = {
            'question': question_data['question'],
            'type': question_data['type'],
        }

        if question_data['type'] == 'multiple_choice':
            if not question_data.get('answers') or len(question_data['answers']) < 2:
                messagebox.showerror("Error", "Multiple choice questions need at least 2 answers")
                return False
            formatted_data.update({
                'answers': question_data['answers'],
                'correctAnswer': question_data['correctAnswer'],
                'image': self.image_entry.get() if hasattr(self, 'image_entry') else ''
            })
        
        elif question_data['type'] == 'image_selection':
            if not question_data.get('imageOptions') or len(question_data['imageOptions']) < 2:
                messagebox.showerror("Error", "Minimum 2 afbeeldingen nodig")
                return False
            formatted_data.update({
                'imageOptions': question_data['imageOptions'],
                'correctAnswer': str(question_data['correctAnswer'])
            })

        elif question_data['type'] == 'drag_and_drop':
            if not question_data.get('correctPositions'):
                messagebox.showerror("Error", "Minimum 1 positie nodig")
                return False
            formatted_data.update({
                    'correctPositions': question_data['correctPositions'],
                    'image': self.image_entry.get() if hasattr(self, 'image_entry') else ''
                })
        
        elif question_data['type'] == 'open':
            formatted_data['correctAnswer'] = question_data['correctAnswer']

        # Optionele velden
        if question_data.get('explanation'):
            formatted_data['explanation'] = question_data['explanation']
        if question_data.get('context'):
            formatted_data['context'] = question_data['context']
        if question_data.get('terms'):
            formatted_data['terms'] = question_data['terms']
        if question_data.get('image'):
            formatted_data['image'] = question_data['image']

        # Voeg de parent informatie toe
        formatted_data['parent'] = question_data.get('parent', '')

        #Update de vraag in de database
        try:
            response_data = await self.app.api_client.post('create_question', formatted_data)
            messagebox.showinfo("Success", "Vraag succesvol aangemaakt!")
            
            # Refresh de lijst
            if 'Examen' in formatted_data['parent']: #Elk examen begint met 'Examen'
                await self.app.show_examens()
            else:
                await self.app.show_onderdelen()
            return True

        except Exception as e:
            messagebox.showerror("Error", f"Fout bij aanmaken van vraag: {str(e)}")
            return False

    async def update_feedback_status(self, feedback_id, new_status):
        """Update de status van een feedback item, wanneer je op opslaan drukt bij feedback"""
        try:
            data = {
                'feedbackId': feedback_id,
                'status': new_status
            }
            
            await self.app.api_client.put('update_feedback', data)
            messagebox.showinfo("Success", "Feedback status succesvol bijgewerkt!")
            # Refresh de lijst
            await self.app.show_feedback()
            
        except Exception as e:
            messagebox.showerror("Error", f"Fout bij bijwerken van feedback status: {str(e)}")
    
    def show_feedback_rapport_ui(self, feedback_data):
        """Maak de feedback export view, voor show_feedback_rapport"""
        self.clear_content()
        
        # Create main container with scrollbar
        main_container = self.create_scrollable_frame(self.content_frame)
        
        # Header
        header_frame = tk.Frame(main_container, padx=20, pady=10)
        header_frame.pack(fill='x')
        
        tk.Label(header_frame,text="Feedback Export",font=('Arial', 16, 'bold')).pack(side='left')
        
        # Export knop
        button_frame = tk.Frame(header_frame)
        button_frame.pack(side='right')
        
        ttk.Button(button_frame,text="Export als CSV",style='Accent.TButton',
            command=lambda: self.export_feedback_to_csv(feedback_data)
        ).pack(side='right', padx=5)
        
        # Statistics
        stats_frame = tk.Frame(main_container, padx=20, pady=10)
        stats_frame.pack(fill='x')
        
        # Tel het aantal feedback items
        total_feedback = len(feedback_data)
        status_counts = {
            'new': 0,
            'in_progress': 0,
            'completed': 0,
            'pending': 0
        }
        
        # Tel het aantal feedback items per status
        for feedback in feedback_data:
            status = feedback.get('status')
            if status in status_counts:
                status_counts[status] += 1
        
        tk.Label(stats_frame,
            text=f"Totaal aantal feedback items: {total_feedback}",
            font=('Arial', 12)
        ).pack(anchor='w')
        
        status_emojis = {
            'new': '🆕',
            'in_progress': '⏳',
            'completed': '✅',
            'pending': '⏳'
        }
        
        for status, count in status_counts.items():
            emoji = status_emojis[status]
            tk.Label(stats_frame, text=f"{emoji} {status.replace('_', ' ').title()}: {count}", font=('Arial', 12)).pack(anchor='w')

    def export_feedback_to_csv(self, feedback_data):
        """Exporteer de feedback naar een csv bestand, voor show_feedback_rapport"""
        try:
            from tkinter import filedialog
            import csv
            from datetime import datetime
            
            # Vraag de gebruiker waar hij het bestand wilt opslaan
            file_path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[("CSV files", "*.csv")], title="Feedback Export opslaan")
            
            if not file_path:
                return
            
            with open(file_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                # Schrijf de headers voor de csv file
                writer.writerow(['ID', 'Status', 'Subject', 'Feedback', 'Date', 'Question ID', 'User ID'])
                
                # Write data
                for item in feedback_data:
                    date_str = ''
                    if 'date' in item and '_seconds' in item['date']:
                        date = datetime.fromtimestamp(item['date']['_seconds'])
                        date_str = date.strftime('%d-%m-%Y %H:%M')
                    
                    writer.writerow([ #Schrijf de data naar de csv file
                        item.get('id', ''),
                        item.get('status', ''),
                        item.get('subject', ''),
                        item.get('feedback', ''),
                        date_str,
                        item.get('questionId', ''),
                        item.get('userId', '')
                    ])
            
            messagebox.showinfo("Success", "Feedback succesvol geëxporteerd naar CSV!")
        except Exception as e:
            messagebox.showerror("Error", f"Fout bij exporteren naar CSV: {str(e)}")

class QuestionTypeDialog(tk.Toplevel):
    """Popup menu voor het kiezen van het type van een vraag"""

    #! Setup
    def __init__(self, parent):
        super().__init__(parent)
        self.result = None
        
        self.title("Kies vraag type")
        self.geometry("400x500")
        self.resizable(False, False)
        
        # Center van het scherm
        self.center_window()

        #Zorgt ervoor dat de popup gekoppeld wordt aan het parent-venster en dat de user interactie met de popup de focus houdt
        self.transient(parent)
        self.grab_set()
        
        self.create_widgets()

    def center_window(self):
        """Center de popup op het scherm"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'+{x}+{y}')

    #! Maak de UI elementen aan
    def create_widgets(self):
        """Maak de UI elementen aan"""
        # Title
        tk.Label(self, text="Kies het type vraag", font=('Arial', 16, 'bold'), pady=20).pack()

        # Container voor de vraag types
        types_frame = tk.Frame(self)
        types_frame.pack(fill='both', expand=True, padx=20, pady=10)

        for type_info in QUESTION_TYPES:
            self.create_type_button(types_frame, type_info) 

    #! Maak een knop aan voor elk type vraag
    def create_type_button(self, parent, type_info):
        """Maak een knop aan voor een vraag type"""
        type_frame = tk.Frame( parent, relief='solid', borderwidth=1,cursor='hand2')
        type_frame.pack(fill='x', pady=5, ipady=10)

        def on_click(event):
            self.select_type(type_info['id'])

        # Icon and title container
        header = tk.Frame(type_frame)
        header.pack(fill='x', padx=10, pady=(5, 0))
        
        # Icon
        icon_label = tk.Label(header, text=type_info['icon'], font=('Arial', 14), cursor='hand2')
        icon_label.pack(side='left')

        # Title
        title_label = tk.Label( header, text=type_info['title'], font=('Arial', 12, 'bold'), cursor='hand2')
        title_label.pack(side='left', padx=10)

        # Description
        desc_label = tk.Label(type_frame, text=type_info['description'], wraplength=350, justify='left', cursor='hand2')
        desc_label.pack(fill='x', padx=10, pady=(5, 0))

        # Alles moet dezelfde events binden, want als je op de tekst klikt, moet het ook werken
        for widget in [header, icon_label, title_label, desc_label, type_frame]:
            widget.bind('<Button-1>', on_click)

    def select_type(self, type_id):
        """Selecteer een vraag type"""
        self.result = type_id
        self.destroy() #Sluit de popup

class APIClient:
    """API client class"""
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {
            'x-api-key': api_key,
            'Content-Type': 'application/json'
        }
    
    async def get(self, endpoint_key):
        """GET request"""
        return await self._request(endpoint_key, 'get')
    
    async def post(self, endpoint_key, data):
        """POST request"""
        return await self._request(endpoint_key, 'post', data)
    
    async def put(self, endpoint_key, data):
        """PUT request"""
        return await self._request(endpoint_key, 'put', data)
    
    async def delete(self, endpoint_key, data=None):
        """DELETE request"""
        return await self._request(endpoint_key, 'delete', data)
    
    async def _request(self, endpoint_key, method, data=None):
        """Request handler"""
        async with aiohttp.ClientSession() as session:
            try:
                endpoint = f"{self.base_url}{API_CONFIG['ENDPOINTS'][endpoint_key]}" #Endpoint opbouwen
                async with getattr(session, method)(
                    endpoint,
                    headers=self.headers,
                    json=data
                ) as response:
                    # Zowel 200 als 201 worden als succes status codes geaccepteerd, dit is namelijk niet consistent in de API
                    if response.status in [200, 201]:
                        return await response.json()
                    error_text = await response.text()
                    raise Exception(f"API Fout: {response.status}, {error_text}")
            except Exception as e:
                raise Exception(f"Request gefaald: {str(e)}")

class App:
    """Main application class met alle globale functies"""
    
    # Start functies
    def __init__(self):
        self.setup_api_config()
        self.setup_window()
        self.setup_async_loop()
        self.setup_frames()

    def setup_api_config(self):
        """Haal de API key en url op uit de .env file"""
        load_dotenv()
        self.api_url = os.getenv('API_URL')
        self.api_key = os.getenv('API_KEY')
        self.api_client = APIClient(self.api_url, self.api_key)
        if not self.api_key or not self.api_url:
            raise ValueError("API_KEY en/of API_URL niet gevonden in .env file, check het verslag voor de api_key en api_url")

    def setup_window(self):
        """Venster instellingen"""
        self.root = tk.Tk()
        self.root.title("Theorio Cursusbeheer")
        self.root.geometry("1200x800")
        self.root.configure(bg='#3374FF') #blauw

    def setup_frames(self):
        """Frames opzetten"""
        self.nav_frame = NavigatieBalk(self.root, self)
        self.frame = tk.Frame(self.root, bg='#3374FF')
        self.frame.pack(fill='both', expand=True)
        self.lijst_frame = LijstFrame(self.frame, self)
        self.details_frame = DetailsFrame(self.frame, self)

    # Async loop setup, Maak een aparte loop, in een aparte thread, voor async functies, zodat de GUI niet vastloopt 
    def setup_async_loop(self):
        """Maak de async event loop aan"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.loop_thread.start()

    def _run_event_loop(self):
        """Run de async event loop"""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def handle_async_button(self, coro):
        """Async knop, voert de coroutine (async functie) in een aparte thread uit zodat de GUI niet vastloopt"""
        asyncio.run_coroutine_threadsafe(coro, self.loop)

    #! Navigatie knoppen - Aangeroepen vanuit NavigatieBalk class
    async def show_onderdelen(self):
        """Onderdelen ophalen van de API en tonen in de lijst"""
        self.lijst_frame.update_lijst([], loading=True) #Loading indicator aanzetten
        try:
            data = await self.api_client.get('subjects')
            items = [self.format_subject_data(subject) for subject in data['subjects']] # Pas de data aan naar de verwachte structuur van de lijst
            self.lijst_frame.update_lijst(items, loading=False) #Loading indicator uitzetten en lijst tonen
        except Exception as e:
            self.show_error(f"Fout b fetching subjects: {str(e)}")
            self.lijst_frame.update_lijst([], loading=False) #Loading indicator uitzetten bij fout en lege lijst tonen

    async def show_exams(self):
        """Examens ophalen van de API en tonen in de lijst"""
        self.lijst_frame.update_lijst([], loading=True) #Loading indicator aanzetten
        try:
            data = await self.api_client.get('exams')

            # De data vanuit de server is eigenlijk 3 arrays voor elk onderdeel in het examen (gevaarherkenning, inzicht, kennis)
            # Maar we maken hier 3 aparte items in de lijst voor elk onderdeel dus je krijgt Examen 1 - Gevaarherkenning, Examen 1 - Inzicht, Examen 1 - Kennis etc.
            # Idealiter zou dit al gedaan moeten zijn op de server side, maar dit werkt ook
            exams = []
            for exam in data['exams']:
                exam_categories = []
                
                categories = {
                    'gevaarherkenning': 'Gevaarherkenning',
                    'inzicht': 'Inzicht',
                    'kennis': 'Kennis'
                }
                
                for category, display_name in categories.items():
                    if category in exam and exam[category].get('questions'):
                        category_questions = exam[category]['questions']
                        exam_categories.append({
                            'titel': f"Examen {exam['id']} - {display_name}", #Examen 1 - Gevaarherkenning, etc.
                            'vragen': [self.format_question_data(i, question) # Pas de data aan naar de verwachte structuur van de lijst, en details frame
                                     for i, question in enumerate(category_questions)]
                        })
                
                exams.extend(exam_categories)
            
            self.lijst_frame.update_lijst(exams, loading=False) #Loading indicator uitzetten en lijst updaten
        except Exception as e:
            self.show_error(f"Error fetching exams: {str(e)}")
            self.lijst_frame.update_lijst([], loading=False)

    def show_rapporten(self):
        """Rapporten ophalen van de API en tonen in de lijst"""
        items = ["Export feedback"] #Alleen export feedback is beschikbaar, helaas had ik geen tijd meer om de andere rapporten te implementeren
        self.lijst_frame.update_lijst(items, loading=False) #Lijst tonen

    async def show_feedback(self):
        """Feedback ophalen van de API en tonen in de lijst"""
        self.lijst_frame.update_lijst([], loading=True) #Loading indicator aanzetten
        try:
            data = await self.api_client.get('feedback')
            self.lijst_frame.update_lijst([data.get('feedback', [])], loading=False) #Loading indicator uitzetten en lijst tonen
        except Exception as e:
            self.show_error(f"Error fetching feedback: {str(e)}")
            self.lijst_frame.update_lijst([], loading=False)

    #! Update detail frames - Aangeroepen wanneer je een item selecteert in de lijst
    def show_vraag_details(self, hoofdstuk, vraag_data):
        """Toon de vraag details in het details frame"""
        self.details_frame.show_vraag_ui(hoofdstuk, vraag_data)
    
    def show_feedback_details(self, feedback_data):
        """Toon de feedback details in het details frame"""
        self.details_frame.show_feedback_ui(feedback_data)

    async def show_rapport_feedback_details(self):
        """Toon info van de csv bestand over de feedback in het details frame"""
        self.lijst_frame.update_lijst([], loading=True) #Loading indicator aanzetten, maar eigenlijk zou de details frame moeten laden
        try:
            data = await self.api_client.get('feedback')
            if data:
                self.lijst_frame.update_lijst([], loading=False) #Loading indicator uitzetten, maar de lijst is leeg, maar eigenlijk zou de details frame moeten laden
                self.details_frame.show_feedback_rapport_ui(data.get('feedback', []))
        except Exception as e:
            self.show_error(f"Error exporting feedback: {str(e)}")

    #! Data Formatting Methods
    # Idealiter zou dit niet nodig zijn, maar de data die de API terug geeft is niet helemaal in de verwachte structuur en ik heb geen tijd meer om deze aan te passen
    def format_subject_data(self, subject):
        """Format subject data voor de lijst"""
        return {
            'titel': subject['title'],
            'vragen': [self.format_question_data(i, question) 
                      for i, question in enumerate(subject.get('questions', []))]
        }
    
    # Gebruikt in show_onderdelen en show_exams
    def format_question_data(self, index, question):
        """Format question data voor de lijst"""
        return {
            'titel': f'Vraag {index+1}',
            'vraag_tekst': question['question'],
            'type': question['type'],
            'opties': question.get('answers', []) if question.get('type') == 'multiple_choice' else [],
            'antwoord': question.get('correctAnswer', ''),
            'uitleg': question.get('explanation', ''),
            'afbeelding': question.get('image', ''),
            'context': question.get('context', ''),
            'imageOptions': question.get('imageOptions', []),
            'terms': question.get('terms', {}),
            'correctPositions': question.get('correctPositions', []),
            'correctAnswer': question.get('correctAnswer', 0),
            'id': question['id']
        }
    
    #! Error handling
    def show_error(self, message):
        """Foutmelding tonen in een popup"""
        print(f"Error: {message}")
        tk.messagebox.showerror("FOUT:", message)

    #! Applicatie start en cleanup
    def run(self):
        """Run de applicatie"""
        try:
            self.root.mainloop()
        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup, dit is nodig om de async loop te stoppen en de thread te joinen zodat de app niet crasht bij het sluiten"""
        # Used in: run method
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.loop_thread.join()
        self.loop.close()

if __name__ == "__main__":
    app = App()
    app.run()