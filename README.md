# activate virtual environment
source env/bin/activate

# create virtual environment
python3 -m venv env

# shortcut to run python file
CMD + CTRL + N

# Theorio Vragenbeheer Systeem
Desktop applicatie voor het beheren en analyseren van vragen voor de Theorio app.

## Functionaliteiten
- **Vragenbeheer**
  - Maken en bewerken van vragen over hoofdstukken en examens
  - Drag-and-drop vraag organisatie (optioneel)
  - Bulk import/export functionaliteit (optioneel)
  - Ondersteuning voor verschillende vraagtypen (multiple choice, open vragen, etc.)

- **Gebruikersfeedback Verwerking**
  - Beoordelen en verwerken van gebruikersfeedback
  - Direct vragen bewerken vanuit feedback overzicht (optioneel)

- **Analyses**
  - Analyse van vraagmoeilijkheid (optioneel)
  - Inzicht in gebruikersgedrag (optioneel)

## Technische Stack
- Frontend: Python (Tkinter)
- Backend: NodeJS
- Database: Firestore
- Hosting: Google Cloud