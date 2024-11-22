import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import asyncio
from functools import partial
import threading
import aiohttp
from dotenv import load_dotenv
import os
import io
from tkinter import messagebox

class NavigatieBalk(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.pack(fill='x', padx=10, pady=10)

        # Knoppen met async handlers
        self.button = ttk.Button(self, text="📘 Onderdelen",  command=lambda: app.handle_async_button(app.toon_onderdelen()))
        self.button.pack(side='left', padx=10, pady=10)

        self.button2 = ttk.Button(self, text="📝 Examens", command=app.toon_examens)
        self.button2.pack(side='left', padx=5, pady=10)

        self.button3 = ttk.Button(self, text="📊 Rapporten", command=app.toon_rapporten)
        self.button3.pack(side='left', padx=5, pady=10)

        self.button4 = ttk.Button(self, text="💬 Feedback", command=app.toon_feedback)
        self.button4.pack(side='left', padx=5, pady=10)

        #Logo
        logo = Image.open("logo.png")
        logo = logo.convert("RGBA")
        resized_logo = logo.resize((128, 56))
        self.logo = ImageTk.PhotoImage(resized_logo)
        self.logo_label = tk.Label(self, image=self.logo)
        self.logo_label.pack(side='right')
     
class LijstFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.pack(fill='both', side='left', padx=10, pady=10, expand=False)
        self.configure(width=300)
        self.pack_propagate(False)
        self.app = app
        self.vraag_data = {}

        # Container frame for loading and tree
        self.container = tk.Frame(self)
        self.container.pack(fill='both', expand=True)

        # Loading label
        self.loading_label = tk.Label(
            self.container,
            text="🔄 Ophalen van data...",
            font=('Arial', 12),
            pady=20
        )

        # Treeview voor dropdown functionaliteit
        self.tree = ttk.Treeview(self.container)
        self.tree.pack(fill='both', expand=True)
        
        # Maak de treeview interactief
        self.tree.bind('<<TreeviewSelect>>', self.on_select)

    def on_select(self, event):
        selection = self.tree.selection()
        if not selection:  #Niks geselecteerd
            return
        
        selected_item = selection[0]
        parent_id = self.tree.parent(selected_item)
        
        if parent_id:  # Dit is een vraag, want er is een parent dus examen of onderdeel
            vraag_data = self.vraag_data.get(selected_item)
            if vraag_data:
                parent_text = self.tree.item(parent_id)['text']
                self.app.toon_vraag_details(
                    hoofdstuk=parent_text, #neem hoofdstuk en vraag data mee naar de detailsframe
                    vraag_data=vraag_data
                )
        elif 'Rapport' in self.tree.item(selected_item)['text']: # Dit is een rapport
            self.app.toon_rapport_details(self.tree.item(selected_item)['text'])
        elif 'Feedback' in self.tree.item(selected_item)['text']: # Dit is feedback
            self.app.toon_feedback_details(self.tree.item(selected_item)['text'])

    def update_lijst(self, items, loading=True):
        if loading:
            self.tree.pack_forget() # Verwijder tree
            self.loading_label.pack(fill='both', expand=True) # Toon loading label
            self.update()  # Forceer update
            return

        # Toon tree en verwijder loading label
        self.loading_label.pack_forget()
        self.tree.pack(fill='both', expand=True)
        
        # Verwijder alle items
        self.vraag_data.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Voeg nieuwe items toe
        for item in items:
            if isinstance(item, dict):  # Onderdelen, Examens want die zijn dictionaries
                # Voeg hoofdstuk/examen toe als parent
                parent = self.tree.insert("", "end", text=item['titel'])
                
                # Voeg vragen toe als children
                for vraag in item['vragen']:
                    # Maak een dictionary aan met de vraag data
                    unique_id = item['titel']+'-'+vraag['id']+'-'+vraag['titel']
                    self.vraag_data[unique_id] = vraag
                    # Voeg vraag toe aan treeview onder de parent
                    self.tree.insert(parent, "end", iid=unique_id, text=vraag['vraag_tekst'])
            else:  # Rapporten, Feedback (strings)
                self.tree.insert("", "end", text=str(item))

        print("VRAAG DATA:", self.vraag_data)

class DetailsFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.pack(fill='both', side='right', padx=10, pady=10, expand=True)
        
        # Container die aanpast voor question, rapport en feedback details
        self.content_frame = tk.Frame(self)
        self.content_frame.pack(fill='both', expand=True)

        # Bewaar de geladen afbeeldingen om garbage collection te voorkomen
        self.loaded_images = []

    # laad url images met TKinter
    async def load_image_from_url(self, url, size=(100, 100)):
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
            print(f"Error loading image from {url}: {e}")
            return None

    def toon_vraag_ui(self, hoofdstuk, vraag_data):
        self.clear_content()
        self.loaded_images = []
        
        # Canvas voor scrollen
        canvas = tk.Canvas(self.content_frame)
        scrollbar = ttk.Scrollbar(self.content_frame, orient='vertical', command=canvas.yview)
        main_container = tk.Frame(canvas)
        
        # Scrollbar
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        
        # Canvas window
        canvas_window = canvas.create_window((0, 0), window=main_container, anchor='nw')
        
        # scrollgebied
        def configure_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox('all'))
        main_container.bind('<Configure>', configure_scroll_region)
        
        # Header
        header_frame = tk.Frame(main_container, padx=20, pady=10)
        header_frame.pack(fill='x')
        
        # Links
        header_left = tk.Frame(header_frame)
        header_left.pack(side='left')
        
        # Rechts
        header_right = tk.Frame(header_frame)
        header_right.pack(side='right')
        
        tk.Label(
            header_left,
            text=f"📘 {hoofdstuk} - {vraag_data['id']}",
            font=('Arial', 16, 'bold'),
        ).pack(anchor='w')
        
        # Opslaan knop
        save_button = ttk.Button(
            header_right,
            text="Opslaan",
            style='Accent.TButton',
            width=20
        )
        save_button.pack(pady=5)
        
        # Content container 
        content_container = tk.Frame(main_container, padx=20)
        content_container.pack(fill='both', expand=True)
        
        # Links
        left_column = tk.Frame(content_container)
        left_column.pack(side='left', fill='both', expand=True, padx=(0, 10))

        # Antwoord frame
        answer_frame = tk.Frame(left_column)
        answer_frame.pack(fill='x', pady=10)    
        
        # Vraag context
        if vraag_data['type'] in ['open', 'multiple_choice']:
            context_frame = tk.Frame(left_column)
            context_frame.pack(fill='x', pady=10)
            
            tk.Label(
                context_frame,
                text="Context:",
                font=('Arial', 12, 'bold'),
            ).pack(anchor='w')
            
            context_text = tk.Text(
                context_frame,
                height=5,
                font=('Arial', 11),
                width=30,
                wrap='word',
            )
            context_text.pack(fill='x', pady=5)
            if 'context' in vraag_data:
                context_text.insert('1.0', vraag_data['context'])
        
        # Vraag frame
        question_frame = tk.Frame(left_column)
        question_frame.pack(fill='x', pady=10)
        
        tk.Label(
            question_frame,
            text="Vraag:",
            font=('Arial', 12, 'bold'),
        ).pack(anchor='w')
        
        vraag_text = tk.Text(
            question_frame,
            height=4,
            font=('Arial', 11),
            wrap='word',
        )
        vraag_text.pack(fill='x', pady=5)
        vraag_text.insert('1.0', vraag_data['vraag_tekst'])

        # Begrippen frame
        if vraag_data['type'] in ['open', 'multiple_choice']:
            terms_frame = tk.Frame(answer_frame)
            terms_frame.pack(fill='x', pady=(20, 10))
            
            # Header with add button side by side
            header_frame = tk.Frame(terms_frame)
            header_frame.pack(fill='x', pady=(0, 5))
            
            tk.Label(
                header_frame,
                text="Begrippen:",
                font=('Arial', 12, 'bold'),
            ).pack(side='left')
            
            ttk.Button(
                header_frame,
                text="+ Nieuw begrip",
                style='Accent.TButton',
                width=15
            ).pack(side='right')
            
            # Begrippen container
            terms_container = tk.Frame(terms_frame)
            terms_container.pack(fill='x')
            
            # Voeg elk begrip en zijn definitie toe
            for term, definition in vraag_data.get('terms', {}).items():
                term_frame = tk.Frame(terms_container)
                term_frame.pack(fill='x', pady=2)
                
                # Left side - Term
                term_left = tk.Frame(term_frame)
                term_left.pack(side='left', fill='x', expand=True, padx=(0, 5))
                
                tk.Label(
                    term_left,
                    text="Term:",
                    font=('Arial', 10, 'bold')
                ).pack(side='left', padx=(0, 5))
                
                term_entry = ttk.Entry(term_left, width=20)
                term_entry.pack(side='left', fill='x', expand=True)
                term_entry.insert(0, term)
                
                # Rechts - Definitie
                def_right = tk.Frame(term_frame)
                def_right.pack(side='left', fill='x', expand=True, padx=(5, 0))
                
                tk.Label(
                    def_right,
                    text="Definitie:",
                    font=('Arial', 10, 'bold')
                ).pack(side='left', padx=(0, 5))
                
                def_entry = ttk.Entry(def_right)
                def_entry.pack(side='left', fill='x', expand=True)
                def_entry.insert(0, definition)
                
                # Verwijder knop
                ttk.Button(
                    term_frame,
                    text="×",
                    width=3,
                    style='Accent.TButton'
                ).pack(side='right', padx=(5, 0))
                
                ttk.Separator(terms_container).pack(fill='x', pady=5)
        
        # Antwoord label - Alleen tonen als niet drag_and_drop
        if vraag_data['type'] != 'drag_and_drop':
            tk.Label(
                answer_frame,
                text="Antwoord:",
                font=('Arial', 12, 'bold'),
            ).pack(anchor='w')
            
            # Vraag type specifieke antwoord UI
            if vraag_data['type'] == 'multiple_choice':
                selected_option = tk.StringVar()
                # Set initial value if correctAnswer exists
                if 'antwoord' in vraag_data:
                    selected_option.set(vraag_data['antwoord'])
                
                for i, optie in enumerate(vraag_data['opties']):
                    rb = ttk.Radiobutton(
                        answer_frame,
                        text=optie,
                        variable=selected_option,
                        value=optie
                    )
                    rb.pack(anchor='w', pady=3)
            
            elif vraag_data['type'] == 'image_selection':
                images_frame = tk.Frame(answer_frame)
                images_frame.pack(fill='x', pady=5)
                
                # Invoerveld voor antwoord in plaats van radio knoppen
                answer_container = tk.Frame(answer_frame)
                answer_container.pack(fill='x', pady=5)
                
                tk.Label(
                    answer_container,
                    text="Antwoord (1-4):",
                    font=('Arial', 10)
                ).pack(side='left', padx=(0, 5))
                
                answer_entry = ttk.Entry(
                    answer_container,
                    width=5
                )
                answer_entry.pack(side='left')
                if 'correctAnswer' in vraag_data:
                    answer_entry.insert(0, str(vraag_data['correctAnswer']))
                
                # 2x2 grid van afbeeldingen
                for i, image_url in enumerate(vraag_data['imageOptions'], 1):
                    # Bereken grid positie
                    row = (i-1) // 2
                    col = (i-1) % 2
                    
                    # Frame voor elke afbeelding
                    option_frame = tk.Frame(images_frame)
                    option_frame.grid(row=row, column=col, padx=5, pady=5)
                    
                    # Laad en tonen afbeelding
                    self.handle_async_button(self.load_and_display_option_image(
                        option_frame, 
                        image_url, 
                        i
                    ))

            elif vraag_data['type'] == 'open':
                antwoord_text = tk.Text(
                    answer_frame,
                    height=4,
                    font=('Arial', 11),
                    wrap='word',
                    width=30
                )
                antwoord_text.pack(fill='x', pady=5)
                if 'antwoord' in vraag_data:
                    antwoord_text.insert('1.0', vraag_data['antwoord'])

        # Rechts - Afbeeldingen
        right_column = tk.Frame(content_container)
        right_column.pack(side='right', fill='both', padx=(10, 0))
        
        if vraag_data.get('afbeelding'):
            self.handle_async_button(self.load_and_display_question_image(
                right_column, 
                vraag_data['afbeelding']
            ))

        # Feedback sectie onderaan
        uitleg_frame = tk.Frame(main_container, padx=20)
        uitleg_frame.pack(fill='x', pady=10)
        
        tk.Label(
            uitleg_frame,
            text="Uitleg:",
            font=('Arial', 12, 'bold'),
        ).pack(anchor='w')
        
        uitleg_text = tk.Text(
            uitleg_frame,
            height=3,
            font=('Arial', 11),
            wrap='word',
            width=30
        )
        uitleg_text.pack(fill='x', pady=5)
        
        # Voeg uitleg toe als deze bestaat
        if 'uitleg' in vraag_data:
            uitleg_text.insert('1.0', vraag_data['uitleg'])

        # Voeg drag and drop positie sectie toe na het antwoord
        if vraag_data['type'] == 'drag_and_drop':
            positions_frame = tk.Frame(main_container, padx=20)
            positions_frame.pack(fill='x', pady=10)
            
            # Header met toevoeg knop
            positions_header = tk.Frame(positions_frame)
            positions_header.pack(fill='x', pady=(0, 5))
            
            tk.Label(
                positions_header,
                text="Posities:",
                font=('Arial', 12, 'bold'),
            ).pack(side='left')
            
            ttk.Button(
                positions_header,
                text="+ Nieuwe positie",
                style='Accent.TButton',
                width=15,
                command=lambda: self.add_position_entry(positions_container)
            ).pack(side='right')
            
            # Container voor positie invoer
            positions_container = tk.Frame(positions_frame)
            positions_container.pack(fill='x')
            
            # Voeg bestaande posities toe
            for i, pos in enumerate(vraag_data.get('correctPositions', [])):
                self.add_position_entry(
                    positions_container,
                    index=i,
                    x=pos.get('positionX', 0),
                    y=pos.get('positionY', 0)
                )

    def add_position_entry(self, container, index=None, x=0, y=0):
        position_frame = tk.Frame(container)
        position_frame.pack(fill='x', pady=2)
        
        # Positie nummer label
        tk.Label(
            position_frame,
            text=f"Positie {index + 1 if index is not None else len(container.winfo_children()) + 1}:",
            font=('Arial', 10, 'bold')
        ).pack(side='left', padx=(0, 10))
        
        # X positie
        tk.Label(
            position_frame,
            text="X:",
            font=('Arial', 10)
        ).pack(side='left', padx=(0, 5))
        
        x_entry = ttk.Entry(position_frame, width=8)
        x_entry.pack(side='left', padx=(0, 10))
        x_entry.insert(0, str(x))
        
        # Y positie
        tk.Label(
            position_frame,
            text="Y:",
            font=('Arial', 10)
        ).pack(side='left', padx=(0, 5))
        
        y_entry = ttk.Entry(position_frame, width=8)
        y_entry.pack(side='left')
        y_entry.insert(0, str(y))
        
        # Verwijder knop
        ttk.Button(
            position_frame,
            text="×",
            width=3,
            style='Accent.TButton',
            command=lambda: position_frame.destroy()
        ).pack(side='right', padx=(10, 0))
        
        ttk.Separator(container).pack(fill='x', pady=5)

    async def load_and_display_question_image(self, container, image_url):
        photo = await self.load_image_from_url(image_url, size=(200, 200))
        if photo:
            self.loaded_images.append(photo)
            img_frame = tk.Frame(container, relief='solid')
            img_frame.pack(pady=10)
            
            img_label = tk.Label(img_frame, image=photo)
            img_label.pack(padx=10, pady=10)

    async def load_and_display_option_image(self, container, image_url, option_num):
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
                text=f"Optie {option_num}",
                font=('Arial', 10)
            ).pack()

    def toon_rapport_ui(self, rapport_naam):
        self.clear_content()
        
        # Rapport UI
        tk.Label(self.content_frame, text=rapport_naam, font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Statistieken
        stats_frame = tk.Frame(self.content_frame)
        stats_frame.pack(fill='x', pady=10)
        
        tk.Label(stats_frame, text="Aantal vragen beantwoord: 25").pack(anchor='w')
        tk.Label(stats_frame, text="Gemiddelde score: 8.5").pack(anchor='w')
        tk.Label(stats_frame, text="Tijd besteed: 2:30 uur").pack(anchor='w')
        
        # Download knop
        ttk.Button(self.content_frame, text="Download PDF").pack(pady=10)

    def toon_feedback_ui(self, feedback_id):
        self.clear_content()
        
        # Feedback UI
        tk.Label(self.content_frame, text=f"Feedback #{feedback_id}", font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Feedback details
        tk.Label(self.content_frame, text="Student:").pack(anchor='w')
        ttk.Entry(self.content_frame).pack(fill='x', pady=5)
        
        tk.Label(self.content_frame, text="Bericht:").pack(anchor='w')
        feedback_text = tk.Text(self.content_frame, height=10)
        feedback_text.pack(fill='x', pady=5)
        
        # Status dropdown
        tk.Label(self.content_frame, text="Status:").pack(anchor='w')
        status = ttk.Combobox(self.content_frame, values=['Nieuw', 'In behandeling', 'Afgerond'])
        status.pack(fill='x', pady=5)
        
        # Opslaan knop
        ttk.Button(self.content_frame, text="Opslaan").pack(pady=10)

    def clear_content(self):
        # Verwijder alle widgets in content_frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def handle_async_button(self, coro):
        # Haal event loop op van de hoofd App instantie
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(coro, loop)

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Theorio Cursusbeheer")
        self.root.geometry("1200x800")
        self.root.configure(bg='#3374FF')
        
        # Loop voor async functies
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Thread voor event loop, omdat async functies niet in de main thread kunnen worden uitgevoerd
        self.loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.loop_thread.start()
        
        # Navigatie balk
        self.nav_frame = NavigatieBalk(self.root, self)
        self.frame = tk.Frame(self.root, bg='#3374FF')
        self.frame.pack(fill='both', expand=True)
        self.lijst_frame = LijstFrame(self.frame, self)
        self.details_frame = DetailsFrame(self.frame)

        # Laad omgevings variabelen en haal API key op
        load_dotenv()
        self.api_url = "https://europe-west1-tab-prod-cf355.cloudfunctions.net"
        self.api_key = os.getenv('API_KEY')
        if not self.api_key:
            raise ValueError("API_KEY not found in environment variables")

    def _run_event_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def toon_onderdelen(self):
        # Laad status tonen
        self.lijst_frame.update_lijst([], loading=True)
        
        # Haal data op
        items = await self.haal_onderdelen_op()
        
        # Update met werkelijke data en verberg laad status
        self.lijst_frame.update_lijst(items, loading=False)

    async def haal_onderdelen_op(self):
        async with aiohttp.ClientSession() as session:
            headers = {
                'x-api-key': self.api_key
            }
            try:
                endpoint = f"{self.api_url}/http-getAllSubjects"
                async with session.get(endpoint, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        print("API Response:", data)
                        return [
                            {
                                'titel': subject['title'],
                                'vragen': [
                                    {
                                        'titel': f'Vraag {i+1}',
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
                                    } for i, question in enumerate(subject.get('questions', []))
                                ]
                            } for subject in data['subjects']
                        ]
                    else:
                        error_text = await response.text()
                        print(f"API Error: {response.status}, {error_text}")
                        tk.messagebox.showerror("Error", f"API Error: {response.status}, {error_text}")
                        return []
            except Exception as e:
                print(f"Error fetching subjects: {e}")
                tk.messagebox.showerror("Error", f"Error fetching subjects: {e}")
                return []

    def handle_async_button(self, coro):
        # Get the event loop from the main App instance
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(coro, loop)

    def toon_examens(self):
        # Laad status tonen
        self.lijst_frame.update_lijst([], loading=True)
        # Haal data op
        self.handle_async_button(self.haal_examens_op())

    async def haal_examens_op(self):
        # Laad status tonen
        self.lijst_frame.update_lijst([], loading=True)
        
        async with aiohttp.ClientSession() as session:
            headers = {
                'x-api-key': self.api_key
            }
            try:
                endpoint = f"{self.api_url}/http-getAllExams"
                async with session.get(endpoint, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Verwerk elke examen
                        exams = []
                        for exam in data['exams']:
                            exam_categories = []
                            
                            # Maak afzonderlijke entries voor elke categorie
                            categories = {
                                'gevaarherkenning': 'Gevaarherkenning',
                                'inzicht': 'Inzicht',
                                'kennis': 'Kennis'
                            }
                            
                            for category, display_name in categories.items():
                                if category in exam and exam[category].get('questions'):
                                    category_questions = exam[category]['questions']
                                    exam_categories.append({
                                        'titel': f"Examen {exam['id']} - {display_name}",
                                        'vragen': [
                                            {
                                                'titel': f'Vraag {i+1}',
                                                'vraag_tekst': question['question'],
                                                'type': question['type'],
                                                'opties': question.get('answers', []) if question.get('type') == 'multiple_choice' else [],
                                                'antwoord': question.get('correctAnswer', ''),
                                                'uitleg': question.get('explanation', ''),
                                                'afbeelding': question.get('image', ''),
                                                'imageOptions': question.get('imageOptions', []),
                                                'context': question.get('context', ''),
                                                'correctAnswer': question.get('correctAnswer', 0),
                                                'correctPositions': question.get('correctPositions', []),
                                                'terms': question.get('terms', {}),
                                                'id': question['id']
                                            } for i, question in enumerate(category_questions)
                                        ]
                                    })
                            
                            exams.extend(exam_categories)
                        
                        self.lijst_frame.update_lijst(exams, loading=False)
                    else:
                        error_text = await response.text()
                        print(f"API Error: {response.status}, {error_text}")
                        tk.messagebox.showerror("Error", f"API Error: {response.status}, {error_text}")
                        self.lijst_frame.update_lijst([], loading=False)
            except Exception as e:
                print(f"Error fetching exams: {e}")
                tk.messagebox.showerror("Error", f"Error fetching exams: {e}")
                self.lijst_frame.update_lijst([], loading=False)

    def toon_rapporten(self):
        items = ["Rapport Q1", "Rapport Q2", "Rapport Q3", "Jaarrapport"]
        self.lijst_frame.update_lijst(items, loading=False)

    def toon_feedback(self):
        items = ["Feedback 1", "Feedback 2", "Feedback 3"]
        self.lijst_frame.update_lijst(items, loading=False)

    def toon_vraag_details(self, hoofdstuk, vraag_data):
        self.details_frame.toon_vraag_ui(hoofdstuk, vraag_data)
        
    def toon_rapport_details(self, rapport_naam):
        self.details_frame.toon_rapport_ui(rapport_naam)
        
    def toon_feedback_details(self, feedback_id):
        self.details_frame.toon_feedback_ui(feedback_id)

    def run(self):
        try:
            self.root.mainloop()
        finally:
            # Cleanup bij afsluiten
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.loop_thread.join()
            self.loop.close()

if __name__ == "__main__":
    app = App()
    app.run()