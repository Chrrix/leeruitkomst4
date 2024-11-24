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
import json
from datetime import datetime
import traceback

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

        # Style for the Treeview
        style = ttk.Style()
        style.configure("Custom.Treeview", rowheight=40)  # Increase row height
        style.configure("Custom.Treeview.Item", padding=5)

        # Treeview voor dropdown functionaliteit
        self.tree = ttk.Treeview(self.container, style="Custom.Treeview")
        self.tree.pack(fill='both', expand=True)
        
        # Add popup menu
        self.popup_menu = tk.Menu(self, tearoff=0)
        self.popup_menu.add_command(label="+ Maak vraag", command=self.create_new_question)
        
        # Bind right-click to show popup menu
        self.tree.bind('<Button-3>', self.show_popup_menu)
        self.tree.bind('<Button-1>', self.on_click)
        
        # Maak de treeview interactief
        self.tree.bind('<<TreeviewSelect>>', self.on_select)

    def update_lijst(self, items, loading=True):
        if loading:
            self.tree.pack_forget()
            self.loading_label.pack(fill='both', expand=True)
            self.update()
            return

        self.loading_label.pack_forget()
        self.tree.pack(fill='both', expand=True)
        
        # Clear existing items
        self.vraag_data.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Add new items
        for item in items:
            if isinstance(item, dict):
                if 'feedback' in str(item['titel']).lower():  # Check if this is a feedback item
                    # For feedback items, add each feedback directly as a single item
                    for feedback in item['vragen']:
                        unique_id = f"feedback-{feedback['id']}"
                        self.vraag_data[unique_id] = feedback
                        # Create display text from the feedback data
                        status_emoji = {
                            'new': '🆕',
                            'in_progress': '⏳',
                            'completed': '✅',
                            'pending': '⏳'
                        }.get(feedback.get('status', 'new'), '🆕')
                        
                        # Format date if available
                        date_str = ''
                        if 'date' in feedback and '_seconds' in feedback['date']:
                            date = datetime.fromtimestamp(feedback['date']['_seconds'])
                            date_str = date.strftime('%d-%m-%Y %H:%M')
                        
                        display_text = f"{status_emoji} {date_str} - {feedback.get('subject', 'Geen onderwerp')}"
                        self.tree.insert("", "end", iid=unique_id, text=display_text)
                else:  # For other items (onderdelen, examens)
                    # Add chapter/exam as parent
                    parent = self.tree.insert("", "end", text=item['titel'])
                    
                    # Add "+ New question" button as first child
                    self.tree.insert(parent, "end", 
                                   text="+ Nieuwe vraag toevoegen", 
                                   tags=('add_button',),
                                   values=(parent,))
                    
                    # Add questions as children
                    for vraag in item['vragen']:
                        unique_id = item['titel']+'-'+vraag['id']+'-'+vraag['titel']
                        self.vraag_data[unique_id] = vraag
                        self.tree.insert(parent, "end", iid=unique_id, text=vraag['vraag_tekst'])
            else:  # Reports (strings)
                self.tree.insert("", "end", text=str(item))

    def on_click(self, event):
        # Get clicked item
        item = self.tree.identify_row(event.y)
        if not item:
            return
            
        # Check if clicked on parent item
        if not self.tree.parent(item):
            # Check if clicked on "[+ Vraag]" text
            text = self.tree.item(item)['text']
            if "[+ Vraag]" in text:
                self.selected_parent = item
                self.create_new_question()

    def show_popup_menu(self, event):
        # Get the item under cursor
        item = self.tree.identify_row(event.y)
        if item:
            # Only show menu for parent items (chapters/exams)
            if not self.tree.parent(item):
                self.selected_parent = item
                self.popup_menu.post(event.x_root, event.y_root)

    def create_new_question(self):
        if hasattr(self, 'selected_parent'):
            parent_text = self.tree.item(self.selected_parent)['text']
            
            # Show type selection dialog
            dialog = QuestionTypeDialog(self)
            self.wait_window(dialog)
            
            # If a type was selected
            if dialog.result:
                # Create empty question template
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
                
                # Show question details with empty template
                self.app.toon_vraag_details(parent_text, empty_question)

    def on_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        
        selected_item = selection[0]
        selected_text = self.tree.item(selected_item)['text']
        
        # Handle export options
        if selected_text == "Export feedback":
            self.app.handle_async_button(self.app.export_feedback())
            return
        
        # Rest of your existing on_select code...x
        if selected_item.startswith('feedback-'):
            feedback_data = self.vraag_data.get(selected_item)
            if feedback_data:
                self.app.toon_feedback_details(feedback_data)
            return
        
        # Check if this is an "add" button
        if 'add_button' in self.tree.item(selected_item)['tags']:
            # Get parent from values
            parent_id = self.tree.item(selected_item)['values'][0]
            parent_text = self.tree.item(parent_id)['text']
            self.selected_parent = parent_id
            self.create_new_question()
            return
        
        parent_id = self.tree.parent(selected_item)
        
        if parent_id:  # Dit is een vraag, want er is een parent dus examen of onderdeel
            vraag_data = self.vraag_data.get(selected_item)
            if vraag_data:
                parent_text = self.tree.item(parent_id)['text']
                self.app.toon_vraag_details(
                    hoofdstuk=parent_text,
                    vraag_data=vraag_data
                )
        elif 'Rapport' in self.tree.item(selected_item)['text']: # Dit is een rapport
            self.app.toon_rapport_details(self.tree.item(selected_item)['text'])
        elif 'Feedback' in self.tree.item(selected_item)['text']: # Dit is feedback
            self.app.toon_feedback_details(self.tree.item(selected_item)['text'])

class DetailsFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.pack(fill='both', side='right', padx=10, pady=10, expand=True)
        self.app = app
        
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
        # Initialize all possible storage variables
        self.terms_entries = []
        self.position_frames = []
        self.option_entries = []  # Add this for multiple choice
        self.selected_option = None  # Add this for multiple choice
        self.image_urls = []
        self.current_type = vraag_data['type']
        self.image_url = vraag_data.get('image', '')
        self.parent = hoofdstuk  # Store the parent/hoofdstuk

        # Clear and create UI as before
        self.clear_content()
        self.loaded_images = []
        
        main_container = self.create_scrollable_frame(self.content_frame)
        self.create_header(main_container, hoofdstuk, vraag_data)
        content_container = self.create_content_container(main_container)
        
        left_column = self.create_left_column(content_container)
        right_column = self.create_right_column(content_container, vraag_data)
        
        self.create_question_context(left_column, vraag_data)
        self.create_question_frame(left_column, vraag_data)
        self.create_terms_frame(left_column, vraag_data)
        self.create_answer_frame(left_column, vraag_data)
        self.create_feedback_section(main_container, vraag_data)
        self.create_positions_section(main_container, vraag_data)

    def create_scrollable_frame(self, parent):
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)

        canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')

        def configure_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox('all'))

        scrollable_frame.bind('<Configure>', configure_scroll_region)
        return scrollable_frame

    def create_header(self, parent, hoofdstuk, vraag_data):
        header_frame = tk.Frame(parent, padx=20, pady=10)
        header_frame.pack(fill='x')

        header_left = tk.Frame(header_frame)
        header_left.pack(side='left')

        header_right = tk.Frame(header_frame)
        header_right.pack(side='right')

        tk.Label(
            header_left,
            text=f"📘 {hoofdstuk} - {vraag_data['id']}",
            font=('Arial', 16, 'bold'),
        ).pack(anchor='w')

        # Add delete button
        ttk.Button(
            header_right,
            text="Verwijderen",
            style='Accent.TButton',
            width=20,
            command=lambda: self.delete_question(vraag_data['id'])
        ).pack(side='right', padx=(5, 0), pady=5)

        ttk.Button(
            header_right,
            text="Opslaan",
            style='Accent.TButton',
            width=20,
            command=lambda: self.save_question(vraag_data['id'])
        ).pack(side='right', pady=5)

    def save_question(self, question_id):
        # Collect all data from UI elements
        question_data = {
            'type': self.current_type,
            'parent': self.parent  # Use the stored parent value
        }

        # Safely get text from widgets
        def safe_get_text(widget):
            try:
                if widget and widget.winfo_exists():
                    return widget.get('1.0', 'end-1c')
                return ''
            except (tk.TclError, AttributeError):
                return ''

        # Add basic question data
        try:
            question_data['question'] = safe_get_text(self.question_text)
            question_data['explanation'] = safe_get_text(self.explanation_text)
        except Exception as e:
            print(f"Error getting basic question data: {e}")
            messagebox.showerror("Error", "Failed to save question text or explanation")
            return

        # Add type-specific data
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
            print(f"Error getting type-specific data: {e}")
            messagebox.showerror("Error", "Failed to save type-specific question data")
            return

        # Add common optional fields
        try:
            # Context
            if hasattr(self, 'context_text'):
                context = safe_get_text(self.context_text)
                if context:
                    question_data['context'] = context

            # Terms
            if hasattr(self, 'terms_entries'):
                terms = {}
                for term_frame in self.terms_entries:
                    try:
                        term = term_frame.term_entry.get()
                        definition = term_frame.def_entry.get()
                        if term and definition:
                            terms[term] = definition
                    except tk.TclError:
                        continue
                if terms:
                    question_data['terms'] = terms

            # Image
            if hasattr(self, 'image_url') and self.image_url:
                question_data['image'] = self.image_url

        except Exception as e:
            print(f"Error getting optional fields: {e}")
            messagebox.showerror("Error", "Failed to save optional question data")
            return

        # Print the data being sent (for debugging)
        print("Saving question data:", question_data)

        # Choose whether to create or update based on question_id
        if question_id == 'new':
            self.app.handle_async_button(self.create_question(question_data))
        else:
            question_data['id'] = question_id
            self.app.handle_async_button(self.update_question(question_data))

    async def update_question(self, question_data):
        print("Updating question:", question_data)
        async with aiohttp.ClientSession() as session:
            headers = {
                'x-api-key': self.app.api_key,
                'Content-Type': 'application/json'
            }
            try:
                endpoint = f"{self.app.api_url}/http-updateQuestion"
                async with session.put(endpoint, headers=headers, json=question_data) as response:
                    if response.status == 200:
                        messagebox.showinfo("Success", "Question updated successfully!")
                    else:
                        error_text = await response.text()
                        messagebox.showerror("Error", f"Failed to update question: {error_text}")
            except Exception as e:
                messagebox.showerror("Error", f"Error updating question: {str(e)}")

    def create_content_container(self, parent):
        content_container = tk.Frame(parent, padx=20)
        content_container.pack(fill='both', expand=True)
        return content_container

    def create_left_column(self, parent):
        left_column = tk.Frame(parent)
        left_column.pack(side='left', fill='both', expand=True, padx=(0, 10))
        return left_column

    def create_right_column(self, parent, vraag_data):
        right_column = tk.Frame(parent)
        right_column.pack(side='right', fill='both', padx=(10, 0))
        if vraag_data.get('afbeelding'):
            self.handle_async_button(self.load_and_display_question_image(
                right_column, 
                vraag_data['afbeelding']
            ))
        return right_column

    def create_question_context(self, parent, vraag_data):
        if vraag_data['type'] in ['open', 'multiple_choice']:
            try:
                context_frame = tk.Frame(parent)
                context_frame.pack(fill='x', pady=10)
                
                tk.Label(
                    context_frame,
                    text="Context ({} voor termen en [] voor italic):",
                    font=('Arial', 12, 'bold'),
                ).pack(anchor='w')
                
                self.context_text = tk.Text(
                    context_frame,
                    height=5,
                    font=('Arial', 11),
                    width=30,
                    wrap='word',
                )
                self.context_text.pack(fill='x', pady=5)
                
                if 'context' in vraag_data:
                    self.context_text.insert('1.0', vraag_data['context'])
            except Exception as e:
                print(f"Error creating context: {e}")
                self.context_text = None

    def create_question_frame(self, parent, vraag_data):
        question_frame = tk.Frame(parent)
        question_frame.pack(fill='x', pady=10)
        
        tk.Label(
            question_frame,
            text="Vraag:",
            font=('Arial', 12, 'bold'),
        ).pack(anchor='w')
        
        # Create the text widget and store the reference immediately
        self.question_text = tk.Text(  # Changed from vraag_text to self.question_text
            question_frame,
            height=4,
            font=('Arial', 11),
            wrap='word',
        )
        self.question_text.pack(fill='x', pady=5)
        self.question_text.insert('1.0', vraag_data['vraag_tekst'])

    def create_terms_frame(self, parent, vraag_data):
        if vraag_data['type'] in ['open', 'multiple_choice']:
            terms_frame = tk.Frame(parent)
            terms_frame.pack(fill='x', pady=(20, 10))
            
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
                width=15,
                command=lambda: self.create_term_entry(terms_container)
            ).pack(side='right')
            
            terms_container = tk.Frame(terms_frame)
            terms_container.pack(fill='x')
            
            self.terms_entries = []  # Store reference to list of term entries
            for term, definition in vraag_data.get('terms', {}).items():
                self.create_term_entry(terms_container, term, definition)

    def create_term_entry(self, parent, term='', definition=''):
        class TermFrame:  # Helper class to store entry references
            def __init__(self, term_entry, def_entry):
                self.term_entry = term_entry
                self.def_entry = def_entry

        term_frame = tk.Frame(parent)
        term_frame.pack(fill='x', pady=2)
        
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
        
        ttk.Button(
            term_frame,
            text="×",
            width=3,
            style='Accent.TButton',
            command=lambda: (
                term_frame.destroy(),
                self.terms_entries.remove(term_obj)
            )
        ).pack(side='right', padx=(5, 0))
        
        term_obj = TermFrame(term_entry, def_entry)
        self.terms_entries.append(term_obj)
        
        ttk.Separator(parent).pack(fill='x', pady=5)

    def create_answer_frame(self, parent, vraag_data):
        if vraag_data['type'] != 'drag_and_drop':
            answer_frame = tk.Frame(parent)
            answer_frame.pack(fill='x', pady=10)
            
            tk.Label(
                answer_frame,
                text="Antwoord:",
                font=('Arial', 12, 'bold'),
            ).pack(anchor='w')
            
            if vraag_data['type'] == 'multiple_choice':
                self.create_multiple_choice_ui(answer_frame, vraag_data)
            elif vraag_data['type'] == 'image_selection':
                self.create_image_selection_ui(answer_frame, vraag_data)
            elif vraag_data['type'] == 'open':
                self.create_open_question_ui(answer_frame, vraag_data)

    def create_multiple_choice_ui(self, parent, vraag_data):
        self.option_entries = []  # Initialize the list
        
        # Add correct answer field
        correct_answer_frame = tk.Frame(parent)
        correct_answer_frame.pack(fill='x', pady=5)
        
        tk.Label(
            correct_answer_frame,
            text="Correct antwoord:",
            font=('Arial', 10)
        ).pack(side='left', padx=(0, 5))
        
        self.answer_entry = ttk.Entry(correct_answer_frame)  # Store reference
        self.answer_entry.pack(side='left', fill='x', expand=True)
        if 'antwoord' in vraag_data:
            self.answer_entry.insert(0, vraag_data['antwoord'])
        
        # Add separator
        ttk.Separator(parent).pack(fill='x', pady=10)
        
        # Add button to add new option
        add_option_frame = tk.Frame(parent)
        add_option_frame.pack(fill='x', pady=5)
        
        ttk.Button(
            add_option_frame,
            text="+ Nieuwe optie",
            style='Accent.TButton',
            command=lambda: self.add_multiple_choice_option()
        ).pack(side='right')

        # Create options container
        self.options_container = tk.Frame(parent)
        self.options_container.pack(fill='x')

        # Add existing options
        for optie in vraag_data.get('opties', []):
            self.add_multiple_choice_option(optie)

    def add_multiple_choice_option(self, value=''):
        option_frame = tk.Frame(self.options_container)
        option_frame.pack(fill='x', pady=2)
        
        # Create StringVar for the option text
        option_var = tk.StringVar(value=value)
        self.option_entries.append(option_var)
        
        # Create the option entry
        entry = ttk.Entry(
            option_frame,
            textvariable=option_var,
        )
        entry.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        # Add delete button
        ttk.Button(
            option_frame,
            text="×",
            width=3,
            style='Accent.TButton',
            command=lambda: (
                option_frame.destroy(),
                self.option_entries.remove(option_var)
            )
        ).pack(side='left', padx=(5, 0))

    def create_image_selection_ui(self, parent, vraag_data):
        images_frame = tk.Frame(parent)
        images_frame.pack(fill='x', pady=5)
        
        answer_container = tk.Frame(parent)
        answer_container.pack(fill='x', pady=5)
        
        tk.Label(
            answer_container,
            text="Antwoord (0-3):",
            font=('Arial', 10)
        ).pack(side='left', padx=(0, 5))
        
        self.answer_entry = ttk.Entry(answer_container, width=5)  # Store reference
        self.answer_entry.pack(side='left')
        if 'correctAnswer' in vraag_data:
            self.answer_entry.insert(0, str(vraag_data['correctAnswer']))
        
        self.image_urls = vraag_data['imageOptions']  # Store reference to image URLs
        
        for i, image_url in enumerate(self.image_urls, 1):
            row = (i-1) // 2
            col = (i-1) % 2
            option_frame = tk.Frame(images_frame)
            option_frame.grid(row=row, column=col, padx=5, pady=5)
            self.handle_async_button(self.load_and_display_option_image(
                option_frame, 
                image_url, 
                i
            ))

    def create_open_question_ui(self, parent, vraag_data):
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
        uitleg_frame = tk.Frame(parent, padx=20)
        uitleg_frame.pack(fill='x', pady=10)
        
        tk.Label(
            uitleg_frame,
            text="Uitleg:",
            font=('Arial', 12, 'bold'),
        ).pack(anchor='w')
        
        # Create the text widget and store the reference immediately
        self.explanation_text = tk.Text(  # Changed from uitleg_text to self.explanation_text
            uitleg_frame,
            height=3,
            font=('Arial', 11),
            wrap='word',
            width=30
        )
        self.explanation_text.pack(fill='x', pady=5)
        if 'uitleg' in vraag_data:
            self.explanation_text.insert('1.0', vraag_data['uitleg'])

    def create_positions_section(self, parent, vraag_data):
        if vraag_data['type'] == 'drag_and_drop':
            positions_frame = tk.Frame(parent, padx=20)
            positions_frame.pack(fill='x', pady=10)
            
            positions_header = tk.Frame(positions_frame)
            positions_header.pack(fill='x', pady=(0, 5))
            
            tk.Label(
                positions_header,
                text="Posities:",
                font=('Arial', 12, 'bold'),
            ).pack(side='left')
            
            positions_container = tk.Frame(positions_frame)
            positions_container.pack(fill='x')
            
            self.position_frames = []  # Store reference to position frames
            
            ttk.Button(
                positions_header,
                text="+ Nieuwe positie",
                style='Accent.TButton',
                width=15,
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
        class PositionFrame:  # Helper class to store entry references
            def __init__(self, x_entry, y_entry):
                self.x_entry = x_entry
                self.y_entry = y_entry

        position_frame = tk.Frame(container)
        position_frame.pack(fill='x', pady=2)
        
        tk.Label(
            position_frame,
            text=f"Positie {index + 1 if index is not None else len(self.position_frames) + 1}:",
            font=('Arial', 10, 'bold')
        ).pack(side='left', padx=(0, 10))
        
        tk.Label(
            position_frame,
            text="X:",
            font=('Arial', 10)
        ).pack(side='left', padx=(0, 5))
        
        x_entry = ttk.Entry(position_frame, width=8)
        x_entry.pack(side='left', padx=(0, 10))
        x_entry.insert(0, str(x))
        
        tk.Label(
            position_frame,
            text="Y:",
            font=('Arial', 10)
        ).pack(side='left', padx=(0, 5))
        
        y_entry = ttk.Entry(position_frame, width=8)
        y_entry.pack(side='left')
        y_entry.insert(0, str(y))
        
        pos_obj = PositionFrame(x_entry, y_entry)
        self.position_frames.append(pos_obj)
        
        ttk.Button(
            position_frame,
            text="×",
            width=3,
            style='Accent.TButton',
            command=lambda: (
                position_frame.destroy(),
                self.position_frames.remove(pos_obj)
            )
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
                text=f"Optie {option_num-1}",
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

    def toon_feedback_ui(self, feedback_data):
        self.clear_content()
        
        # Create main container
        main_container = self.create_scrollable_frame(self.content_frame)
        
        # Header
        header_frame = tk.Frame(main_container, padx=20, pady=10)
        header_frame.pack(fill='x')
        
        tk.Label(
            header_frame,
            text=f"Feedback: {feedback_data.get('subject', '')}",
            font=('Arial', 16, 'bold')
        ).pack(side='left')
        
        # Create a frame for status controls
        status_controls_frame = tk.Frame(main_container, padx=20, pady=10)
        status_controls_frame.pack(fill='x')
        
        # Status label and dropdown on the left
        status_left_frame = tk.Frame(status_controls_frame)
        status_left_frame.pack(side='left')
        
        tk.Label(
            status_left_frame,
            text="Status:",
            font=('Arial', 12, 'bold')
        ).pack(side='left', padx=(0, 10))
        
        status_var = tk.StringVar(value=feedback_data.get('status', 'pending'))
        status_dropdown = ttk.Combobox(
            status_left_frame,
            textvariable=status_var,
            values=['pending', 'in_progress', 'completed'],
            state='readonly',
            width=20
        )
        status_dropdown.pack(side='left')
        
        # Save button on the right
        ttk.Button(
            status_controls_frame,
            text="Opslaan",
            style='Accent.TButton',
            command=lambda: self.app.handle_async_button(
                self.update_feedback_status(
                    feedback_data['id'], 
                    status_var.get()
                )
            )
        ).pack(side='right')
        
        # Question ID section
        if feedback_data.get('questionId'):
            question_id_frame = tk.Frame(main_container, padx=20, pady=10)
            question_id_frame.pack(fill='x')
            
            tk.Label(
                question_id_frame,
                text="Vraag ID:",
                font=('Arial', 12, 'bold')
            ).pack(side='left', padx=(0, 10))
            
            tk.Label(
                question_id_frame,
                text=feedback_data['questionId'],
                font=('Arial', 12)
            ).pack(side='left')
            
        
        # Date
        if 'date' in feedback_data:
            date_seconds = feedback_data['date'].get('_seconds', 0)
            date_str = datetime.fromtimestamp(date_seconds).strftime('%d-%m-%Y %H:%M')
            tk.Label(
                status_controls_frame,
                text=f"Datum: {date_str}",
                font=('Arial', 12)
            ).pack(side='right')
        
        # User info
        if feedback_data.get('userId'):
            user_frame = tk.Frame(main_container, padx=20, pady=10)
            user_frame.pack(fill='x')
            
            tk.Label(
                user_frame,
                text=f"Gebruiker ID: {feedback_data['userId']}",
                font=('Arial', 12)
            ).pack(anchor='w')
        
        # Feedback content
        content_frame = tk.Frame(main_container, padx=20, pady=10)
        content_frame.pack(fill='both', expand=True)
        
        tk.Label(
            content_frame,
            text="Feedback:",
            font=('Arial', 12, 'bold')
        ).pack(anchor='w')
        
        feedback_text = tk.Text(
            content_frame,
            height=10,
            font=('Arial', 11),
            wrap='word'
        )
        feedback_text.pack(fill='both', expand=True, pady=5)
        feedback_text.insert('1.0', feedback_data.get('feedback', ''))
        feedback_text.config(state='disabled')

    def clear_content(self):
        # Verwijder alle widgets in content_frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def handle_async_button(self, coro):
        # Haal event loop op van de hoofd App instantie
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(coro, loop)

    def delete_question(self, question_id):
        # Show confirmation dialog
        if messagebox.askyesno("Bevestiging", "Weet je zeker dat je deze vraag wilt verwijderen?"):
            self.app.handle_async_button(self.delete_question_request(question_id))

    async def delete_question_request(self, question_id):
        async with aiohttp.ClientSession() as session:
            headers = {
                'x-api-key': self.app.api_key,
                'Content-Type': 'application/json'
            }
            try:
                endpoint = f"{self.app.api_url}/http-deleteQuestion"
                async with session.delete(endpoint, headers=headers, json={'id': question_id}) as response:
                    if response.status == 200:
                        messagebox.showinfo("Success", "Vraag succesvol verwijderd!")
                        # Refresh the list after deletion
                        await self.app.toon_onderdelen()
                    else:
                        error_text = await response.text()
                        messagebox.showerror("Error", f"Fout bij verwijderen van vraag: {error_text}")
            except Exception as e:
                messagebox.showerror("Error", f"Fout bij verwijderen van vraag: {str(e)}")

    async def create_question(self, question_data):
        print("create_question: ", question_data)
        # Validate required fields
        required_fields = ['question', 'type']
        missing_fields = [field for field in required_fields if not question_data.get(field)]
        
        if missing_fields:
            messagebox.showerror("Error", f"Missing required fields: {', '.join(missing_fields)}")
            return False

        # Format the data to match the cloud function expectations
        formatted_data = {
            'question': question_data['question'],
            'type': question_data['type'],
        }

        # Add type-specific data
        if question_data['type'] == 'multiple_choice':
            if not question_data.get('answers') or len(question_data['answers']) < 2:
                messagebox.showerror("Error", "Multiple choice questions need at least 2 answers")
                return False
            formatted_data.update({
                'answers': question_data['answers'],
                'correctAnswer': question_data['correctAnswer'] or question_data['answers'][0]  # Default to first answer if none selected
            })
        
        elif question_data['type'] == 'image_selection':
            if not question_data.get('imageOptions') or len(question_data['imageOptions']) < 2:
                messagebox.showerror("Error", "Image selection questions need at least 2 images")
                return False
            formatted_data.update({
                'imageOptions': question_data['imageOptions'],
                'correctAnswer': str(question_data.get('correctAnswer', '0'))  # Default to '0' if none selected
            })

        elif question_data['type'] == 'drag_and_drop':
            if not question_data.get('correctPositions'):
                messagebox.showerror("Error", "Please add at least one position")
                return False
            formatted_data.update({
                'correctPositions': question_data['correctPositions'],
                'correctAnswer': 'positions'  # Fixed value for drag_and_drop
            })
        
        elif question_data['type'] == 'open':
            # For open questions, use explanation as correctAnswer if no specific answer is provided
            formatted_data['correctAnswer'] = question_data.get('explanation', '')

        # Add optional fields if they exist
        if question_data.get('explanation'):
            formatted_data['explanation'] = question_data['explanation']
        if question_data.get('context'):
            formatted_data['context'] = question_data['context']
        if question_data.get('terms'):
            formatted_data['terms'] = question_data['terms']
        if question_data.get('image'):
            formatted_data['image'] = question_data['image']

        # Add parent information to formatted data
        formatted_data['parent'] = question_data.get('parent', '')

        # Make API request
        async with aiohttp.ClientSession() as session:
            headers = {
                'x-api-key': self.app.api_key,
                'Content-Type': 'application/json'
            }
            try:
                endpoint = f"{self.app.api_url}/http-createQuestion"
                async with session.post(endpoint, headers=headers, json=formatted_data) as response:
                    if response.status == 201:
                        response_data = await response.json()
                        messagebox.showinfo("Success", "Question created successfully!")
                        # Refresh the appropriate section based on parent
                        if 'Examen' in formatted_data['parent']:
                            await self.app.toon_examens()
                        else:
                            await self.app.toon_onderdelen()
                        return True
                    else:
                        error_text = await response.text()
                        error_data = json.loads(error_text)
                        messagebox.showerror("Error", f"Failed to create question: {error_data.get('message', error_text)}")
                        return False
            except Exception as e:
                messagebox.showerror("Error", f"Error creating question: {str(e)}")
                return False

    async def load_and_display_profile_image(self, container, image_url, size=(50, 50)):
        photo = await self.load_image_from_url(image_url, size)
        if photo:
            self.loaded_images.append(photo)
            img_label = tk.Label(container, image=photo)
            img_label.pack(side='right', padx=10)

    async def update_feedback_status(self, feedback_id, new_status):
        """Update the status of a feedback item"""
        async with aiohttp.ClientSession() as session:
            headers = {
                'x-api-key': self.app.api_key,
                'Content-Type': 'application/json'
            }
            try:
                endpoint = f"{self.app.api_url}/http-updateFeedbackStatus"
                data = {
                    'feedbackId': feedback_id,  # Changed from 'id' to 'feedbackId' to match cloud function
                    'status': new_status
                }
                
                async with session.put(endpoint, headers=headers, json=data) as response:
                    if response.status == 200:
                        messagebox.showinfo("Success", "Feedback status updated successfully!")
                        # Refresh the feedback list
                        await self.app.toon_feedback()
                    elif response.status == 429:
                        error_data = await response.json()
                        retry_after = error_data.get('retryAfter', 'unknown time')
                        messagebox.showerror(
                            "Rate Limit Exceeded", 
                            f"Please try again after {retry_after} seconds"
                        )
                    else:
                        error_data = await response.json()
                        error_message = error_data.get('message', 'Unknown error occurred')
                        messagebox.showerror("Error", f"Failed to update feedback status: {error_message}")
            except Exception as e:
                messagebox.showerror("Error", f"Error updating feedback status: {str(e)}")

    def toon_rapport_details(self, rapport_naam):
        if rapport_naam == "Export feedback":
            self.handle_async_button(self.export_feedback())
        else:
            self.details_frame.toon_rapport_ui(rapport_naam)
        
    def toon_feedback_details(self, feedback_id):
        self.details_frame.toon_feedback_ui(feedback_id)

    def toon_feedback_export(self, feedback_data):
        """Display feedback export view"""
        self.clear_content()
        
        # Create main container with scrollbar
        main_container = self.create_scrollable_frame(self.content_frame)
        
        # Header
        header_frame = tk.Frame(main_container, padx=20, pady=10)
        header_frame.pack(fill='x')
        
        tk.Label(
            header_frame,
            text="Feedback Export",
            font=('Arial', 16, 'bold')
        ).pack(side='left')
        
        # Export button
        button_frame = tk.Frame(header_frame)
        button_frame.pack(side='right')
        
        ttk.Button(
            button_frame,
            text="Export als CSV",
            style='Accent.TButton',
            command=lambda: self.export_feedback_to_csv(feedback_data)
        ).pack(side='right', padx=5)
        
        # Statistics
        stats_frame = tk.Frame(main_container, padx=20, pady=10)
        stats_frame.pack(fill='x')
        
        # Calculate statistics
        total_feedback = len(feedback_data)
        status_counts = {
            'new': sum(1 for f in feedback_data if f.get('status') == 'new'),
            'in_progress': sum(1 for f in feedback_data if f.get('status') == 'in_progress'),
            'completed': sum(1 for f in feedback_data if f.get('status') == 'completed'),
            'pending': sum(1 for f in feedback_data if f.get('status') == 'pending')
        }
        
        tk.Label(
            stats_frame,
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
            emoji = status_emojis.get(status, '❓')
            tk.Label(
                stats_frame,
                text=f"{emoji} {status.replace('_', ' ').title()}: {count}",
                font=('Arial', 12)
            ).pack(anchor='w')

    def export_feedback_to_csv(self, feedback_data):
        try:
            from tkinter import filedialog
            import csv
            from datetime import datetime
            
            # Ask user for save location
            file_path = filedialog.asksaveasfilename(
                defaultextension='.csv',
                filetypes=[("CSV files", "*.csv")],
                title="Save Feedback Export"
            )
            
            if not file_path:
                return
            
            with open(file_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                # Write headers
                writer.writerow(['ID', 'Status', 'Subject', 'Feedback', 'Date', 'Question ID', 'User ID'])
                
                # Write data
                for item in feedback_data:
                    # Format date if available
                    date_str = ''
                    if 'date' in item and '_seconds' in item['date']:
                        date = datetime.fromtimestamp(item['date']['_seconds'])
                        date_str = date.strftime('%d-%m-%Y %H:%M')
                    
                    writer.writerow([
                        item.get('id', ''),
                        item.get('status', ''),
                        item.get('subject', ''),
                        item.get('feedback', ''),
                        date_str,
                        item.get('questionId', ''),
                        item.get('userId', '')
                    ])
            
            messagebox.showinfo("Success", "Feedback exported successfully to CSV!")
        except Exception as e:
            messagebox.showerror("Error", f"Error exporting to CSV: {str(e)}")

class QuestionTypeDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.result = None
        
        # Window settings
        self.title("Kies vraag type")
        self.geometry("400x500")
        self.resizable(False, False)
        
        # Center window
        self.center_window()
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        # Create UI
        self.create_widgets()

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'+{x}+{y}')

    def create_widgets(self):
        # Title
        tk.Label(
            self,
            text="Kies het type vraag",
            font=('Arial', 16, 'bold'),
            pady=20
        ).pack()

        # Container for question types
        types_frame = tk.Frame(self)
        types_frame.pack(fill='both', expand=True, padx=20, pady=10)

        question_types = [
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
                'icon': '️'
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

        for type_info in question_types:
            self.create_type_button(types_frame, type_info)

    def create_type_button(self, parent, type_info):
        # Create frame for this type
        type_frame = tk.Frame(
            parent,
            relief='solid',
            borderwidth=1,
            cursor='hand2'  # Change cursor to hand on hover
        )
        type_frame.pack(fill='x', pady=5, ipady=10)

        # Add hover effect and click event to the main frame
        def on_click(event):
            self.select_type(type_info['id'])
        
        def on_enter(event):
            event.widget.configure(background='#f0f0f0')
        
        def on_leave(event):
            event.widget.configure(background='white')

        # Bind events to the main frame
        type_frame.bind('<Button-1>', on_click)
        type_frame.bind('<Enter>', on_enter)
        type_frame.bind('<Leave>', on_leave)

        # Icon and title container
        header = tk.Frame(type_frame)
        header.pack(fill='x', padx=10, pady=(5, 0))
        
        # Make header inherit background color
        header.bind('<Enter>', on_enter)
        header.bind('<Leave>', on_leave)
        header.bind('<Button-1>', on_click)

        # Icon
        icon_label = tk.Label(
            header,
            text=type_info['icon'],
            font=('Arial', 14),
            cursor='hand2'
        )
        icon_label.pack(side='left')

        # Title
        title_label = tk.Label(
            header,
            text=type_info['title'],
            font=('Arial', 12, 'bold'),
            cursor='hand2'
        )
        title_label.pack(side='left', padx=10)

        # Description
        desc_label = tk.Label(
            type_frame,
            text=type_info['description'],
            wraplength=350,
            justify='left',
            cursor='hand2'
        )
        desc_label.pack(fill='x', padx=10, pady=(5, 0))

        # Bind all labels to the same events
        for widget in [icon_label, title_label, desc_label]:
            widget.bind('<Button-1>', on_click)
            widget.bind('<Enter>', on_enter)
            widget.bind('<Leave>', on_leave)

    def select_type(self, type_id):
        self.result = type_id
        self.destroy()

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Theorio Cursusbeheer")
        self.root.geometry("1200x800")
        self.root.configure(bg='#3374FF')
        
        # Loop voor async functies
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Thread voor event loop
        self.loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.loop_thread.start()
        
        # Navigatie balk
        self.nav_frame = NavigatieBalk(self.root, self)
        self.frame = tk.Frame(self.root, bg='#3374FF')
        self.frame.pack(fill='both', expand=True)
        self.lijst_frame = LijstFrame(self.frame, self)
        self.details_frame = DetailsFrame(self.frame, self)

        # Load env variables
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
                        # print("API Response:", data)
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

    async def export_feedback(self):
            """Fetch feedback data and trigger export view"""
            async with aiohttp.ClientSession() as session:
                headers = {
                    'x-api-key': self.api_key
                }
                try:
                    endpoint = f"{self.api_url}/http-getAllFeedback"
                    async with session.get(endpoint, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            self.details_frame.toon_feedback_export(data.get('feedback', []))
                        else:
                            error_text = await response.text()
                            messagebox.showerror("Error", f"Failed to fetch feedback data: {error_text}")
                except Exception as e:
                    messagebox.showerror("Error", f"Error exporting feedback: {str(e)}")
                
    def handle_async_button(self, coro):
        """Handle async operations"""
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
        items = ["Export feedback"]
        self.lijst_frame.update_lijst(items, loading=False)

    def toon_feedback(self):
        # Convert to async call
        self.handle_async_button(self.haal_feedback_op())

    async def haal_feedback_op(self):
        # Show loading state
        self.lijst_frame.update_lijst([], loading=True)
        
        async with aiohttp.ClientSession() as session:
            headers = {
                'x-api-key': self.api_key
            }
            try:
                endpoint = f"{self.api_url}/http-getAllFeedback"
                async with session.get(endpoint, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Create a single feedback container
                        feedback_container = {
                            'titel': 'Feedback',
                            'vragen': []
                        }
                        
                        # Process each feedback item
                        for item in data.get('feedback', []):
                            # Format date if available
                            date = item.get('date', {})
                            date_str = ''
                            if isinstance(date, dict) and '_seconds' in date:
                                date_str = datetime.fromtimestamp(date['_seconds']).strftime('%d-%m-%Y %H:%M')
                            
                            # Create feedback item
                            feedback_item = {
                                'id': item.get('id', ''),
                                'subject': item.get('subject', 'Geen onderwerp'),
                                'feedback': item.get('feedback', ''),
                                'status': item.get('status', 'pending'),
                                'date': date,
                                'questionId': item.get('questionId', ''),
                                'userId': item.get('userId', '')
                            }
                            
                            feedback_container['vragen'].append(feedback_item)
                        
                        # Update list with single feedback container
                        self.lijst_frame.update_lijst([feedback_container], loading=False)
                    else:
                        error_text = await response.text()
                        print(f"API Error: {response.status}, {error_text}")
                        tk.messagebox.showerror("Error", f"API Error: {response.status}, {error_text}")
                        self.lijst_frame.update_lijst([], loading=False)
            except Exception as e:
                print(f"Error fetching feedback: {e}")
                tk.messagebox.showerror("Error", f"Error fetching feedback: {e}")
                self.lijst_frame.update_lijst([], loading=False)

    def toon_vraag_details(self, hoofdstuk, vraag_data):
        self.details_frame.toon_vraag_ui(hoofdstuk, vraag_data)
        
    def toon_rapport_details(self, rapport_naam):
        if rapport_naam == "Export feedback":
            self.handle_async_button(self.export_feedback())
        else:
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