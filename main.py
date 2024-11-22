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

class NavigatieBalk(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.configure(bg='white')
        self.pack(fill='x', padx=10, pady=10)

        # Knoppen met async handlers
        self.button = ttk.Button(
            self, 
            text="📘 Onderdelen", 
            command=lambda: app.handle_async_button(app.toon_onderdelen())
        )
        self.button.pack(side='left', padx=5, pady=10)

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
        self.logo_label = tk.Label(self, image=self.logo, bg='white')
        self.logo_label.pack(side='right')
     
class LijstFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.pack(fill='both', side='left', padx=10, pady=10, expand=True)
        self.app = app
        self.vraag_data = {}

        # Treeview voor dropdown functionaliteit
        self.tree = ttk.Treeview(self)
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

    def update_lijst(self, items):
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
                    unique_id = item['titel']+'-'+vraag['id']
                    self.vraag_data[unique_id] = vraag
                    # Voeg vraag toe aan treeview onder de parent
                    self.tree.insert(parent, "end", iid=unique_id, text=vraag['titel'])
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
        
        # Create main container with scrollbar
        canvas = tk.Canvas(self.content_frame)
        scrollbar = ttk.Scrollbar(self.content_frame, orient='vertical', command=canvas.yview)
        main_container = tk.Frame(canvas)
        
        # Configure scrolling
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        
        # Create window in canvas
        canvas_window = canvas.create_window((0, 0), window=main_container, anchor='nw')
        
        # Configure canvas scrolling
        def configure_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox('all'))
        main_container.bind('<Configure>', configure_scroll_region)
        
        # Header section with better spacing and styling
        header_frame = tk.Frame(main_container, padx=20, pady=10)
        header_frame.pack(fill='x')
        
        tk.Label(
            header_frame,
            text=f"📘 {hoofdstuk} - {vraag_data['id']}",
            font=('Arial', 16, 'bold'),
        ).pack(anchor='w')
        
        # Content container with two columns
        content_container = tk.Frame(main_container, padx=20)
        content_container.pack(fill='both', expand=True)
        
        # Left column for question and text
        left_column = tk.Frame(content_container)
        left_column.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        # Question section
        question_frame = tk.Frame(left_column)
        question_frame.pack(fill='x', pady=10)
        
        tk.Label(
            question_frame,
            text="Vraag:",
            font=('Arial', 12, 'bold'),
        ).pack(anchor='w')
        
        tk.Label(
            question_frame,
            text=vraag_data['vraag_tekst'],
            font=('Arial', 11),
            wraplength=400,
            justify='left',
        ).pack(anchor='w', pady=5)
        
        # Answer section in left column
        answer_frame = tk.Frame(left_column)
        answer_frame.pack(fill='x', pady=10)
        
        tk.Label(
            answer_frame,
            text="Antwoord:",
            font=('Arial', 12, 'bold'),
        ).pack(anchor='w')
        
        
        # Right column for images
        right_column = tk.Frame(content_container)
        right_column.pack(side='right', fill='both', padx=(10, 0))
        
        # If question has an image, load it in the right column
        if vraag_data.get('afbeelding'):
            self.handle_async_button(self.load_and_display_question_image(
                right_column, 
                vraag_data['afbeelding']
            ))
        
        # Answer type handling (similar to before but with better styling)
        if vraag_data['type'] == 'multiple_choice':
            antwoord_var = tk.StringVar(value=vraag_data.get('antwoord', ''))
            for optie in vraag_data['opties']:
                rb = ttk.Radiobutton(
                    answer_frame,
                    text=optie,
                    variable=antwoord_var,
                    value=optie
                )
                rb.pack(anchor='w', pady=3)
                
        elif vraag_data['type'] == 'image_selection':
            # Create frame for image options
            images_frame = tk.Frame(answer_frame)
            images_frame.pack(fill='x', pady=5)
            
            # Create variable for selected answer (1-4)
            antwoord_var = tk.IntVar(value=vraag_data.get('correctAnswer', 0))
            
            # Create 2x2 grid of images
            for i, image_url in enumerate(vraag_data['imageOptions'], 1):
                # Calculate grid position
                row = (i-1) // 2
                col = (i-1) % 2
                
                # Create frame for each image option
                option_frame = tk.Frame(images_frame)
                option_frame.grid(row=row, column=col, padx=5, pady=5)
                
                # Load and display image
                self.handle_async_button(self.load_and_display_option_image(
                    option_frame, 
                    image_url, 
                    i,
                    antwoord_var
                ))
                
        elif vraag_data['type'] == 'open':
            antwoord_text = tk.Text(
                answer_frame,
                height=4,
                font=('Arial', 11),
                wrap='word'
            )
            antwoord_text.pack(fill='x', pady=5)
            if 'antwoord' in vraag_data:
                antwoord_text.insert('1.0', vraag_data['antwoord'])
        
        # Feedback section at the bottom
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
            wrap='word'
        )
        uitleg_text.pack(fill='x', pady=5)
        
        # Add the explanation text if it exists
        if 'uitleg' in vraag_data:
            uitleg_text.insert('1.0', vraag_data['uitleg'])
        
        # Save button with improved styling
        button_frame = tk.Frame(main_container, padx=20, pady=10)
        button_frame.pack(fill='x')
        
        save_button = ttk.Button(
            button_frame,
            text="Opslaan",
            style='Accent.TButton',
            width=20
        )
        save_button.pack(pady=10)

    async def load_and_display_question_image(self, container, image_url):
        photo = await self.load_image_from_url(image_url, size=(100, 100))
        if photo:
            self.loaded_images.append(photo)
            img_frame = tk.Frame(container, relief='solid')
            img_frame.pack(pady=10)
            
            img_label = tk.Label(img_frame, image=photo)
            img_label.pack(padx=10, pady=10)

    async def load_and_display_option_image(self, container, image_url, option_num, var):
        photo = await self.load_image_from_url(image_url, size=(100, 100))
        if photo:
            self.loaded_images.append(photo)
            
            # Create radiobutton with image
            rb = ttk.Radiobutton(
                container,
                image=photo,
                variable=var,
                value=option_num
            )
            rb.pack(padx=5, pady=5)
            
            # Add option number label
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
        # Get the event loop from the main App instance
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(coro, loop)

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Theorio Cursusbeheer")
        self.root.geometry("800x600")
        self.root.configure(bg='#3374FF')
        
        # Event loop voor async functies
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Start de event loop in een aparte thread
        self.loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.loop_thread.start()
        
        # Rest van de initialisatie
        self.nav_frame = NavigatieBalk(self.root, self)
        self.frame = tk.Frame(self.root, bg='#3374FF')
        self.frame.pack(fill='both', expand=True)
        self.lijst_frame = LijstFrame(self.frame, self)
        self.details_frame = DetailsFrame(self.frame)

        # Load environment variables and get API key
        load_dotenv()
        self.api_url = "https://europe-west1-tab-prod-cf355.cloudfunctions.net"
        self.api_key = os.getenv('API_KEY')
        if not self.api_key:
            raise ValueError("API_KEY not found in environment variables")

    def _run_event_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def toon_onderdelen(self):
        # Simuleer async data ophalen
        items = await self.haal_onderdelen_op()
        self.lijst_frame.update_lijst(items)

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
                                        'imageOptions': question.get('imageOptions', []),
                                        'correctAnswer': question.get('correctAnswer', 0),
                                        'id': question['id']
                                    } for i, question in enumerate(subject.get('questions', []))
                                ]
                            } for subject in data['subjects']
                        ]
                    else:
                        print(f"API Error: {response.status}, {await response.text()}")
                        return []
            except Exception as e:
                print(f"Error fetching subjects: {e}")
                return []

    def handle_async_button(self, coro):
        # Get the event loop from the main App instance
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(coro, loop)

    def toon_examens(self):
        items = [
            {
                'titel': 'Examen 2024',
                'vragen': [
                    {
                        'id': 'exam2024_q1',
                        'titel': 'Vraag 1',
                        'vraag_tekst': 'Wat is...',
                        'type': 'multiple_choice',
                        'opties': ['A', 'B', 'C', 'D'],
                        'antwoord': 'B',
                    },
                    {
                        'id': 'exam2024_q2',
                        'titel': 'Vraag 2',
                        'vraag_tekst': 'Leg uit...',
                        'type': 'open',
                        'antwoord': '',
                    }
                ]
            },
            {
                'titel': 'Examen 2023',
                'vragen': [
                    {
                        'id': 'exam2023_q1',
                        'titel': 'Vraag 1',
                        'vraag_tekst': 'Beschrijf...',
                        'type': 'open',
                        'antwoord': '',
                    }
                ]
            }
        ]
        self.lijst_frame.update_lijst(items)

    def toon_rapporten(self):
        items = ["Rapport Q1", "Rapport Q2", "Rapport Q3", "Jaarrapport"]
        self.lijst_frame.update_lijst(items)

    def toon_feedback(self):
        items = ["Feedback 1", "Feedback 2", "Feedback 3"]
        self.lijst_frame.update_lijst(items)

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