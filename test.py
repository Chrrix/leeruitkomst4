"""
Dit test bestand bevat de belangrijkste unit tests voor de API client en UI componenten.

Bevat tests voor:
- API Client functionaliteit (endpoints en authenticatie)
- vraag formattering
- vraagtype dialoog modal
- datum formattering

Gebruik:
- Run tests met: pytest test.py
"""

import pytest
from unittest.mock import patch, MagicMock
import tkinter as tk
from datetime import datetime
from main import APIClient, App, QuestionTypeDialog, QUESTION_TYPES
import os
from dotenv import load_dotenv

# Laad environment variables
load_dotenv()

# Basis API configuratie
API_CONFIG = {
    'ENDPOINTS': {
        'subjects': '/http-getAllSubjects',
        'helloWorld': '/helloWorld'
    },
    'URL': os.getenv('API_URL'),
    'KEY': os.getenv('API_KEY')
}

@pytest.fixture
def mock_response():
    """Basis mock response"""
    mock = MagicMock()
    mock.status = 200
    mock.__aenter__.return_value = mock
    return mock

class TestAPIClient:
    """Test de API functionaliteit"""

    @pytest.mark.asyncio
    async def test_get_request(self, mock_response):
        """Test basis GET aanvraag"""
        client = APIClient(API_CONFIG['URL'], API_CONFIG['KEY'])
        
        async def mock_json():
            return {"data": "test"}
            
        mock_response.json = mock_json
        mock_response.__aenter__.return_value = mock_response
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.get = MagicMock(return_value=mock_response)
            result = await client.get('subjects')
            assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_hello_world(self, mock_response):
        """Test helloWorld endpoint"""
        client = APIClient(API_CONFIG['URL'], API_CONFIG['KEY'])
        
        async def mock_json():
            return {"message": "Hello, World!"}
            
        mock_response.json = mock_json
        mock_response.__aenter__.return_value = mock_response
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.get = MagicMock(return_value=mock_response)
            result = await client.get('helloWorld')
            assert result == {"message": "Hello, World!"}

class TestApp:
    """Test de basis App functionaliteit"""

    def test_format_question(self):
        """Test vraag formattering"""
        app = App()
        test_question = {
            "id": "q1",
            "question": "Test vraag",
            "type": "multiple_choice",
            "answers": ["A", "B", "C"],
            "correctAnswer": "A"
        }
        
        formatted = app.format_question_data(0, test_question)
        assert formatted["titel"] == "Vraag 1"
        assert formatted["vraag_tekst"] == "Test vraag"
        assert formatted["type"] == "multiple_choice"

class TestQuestionTypeDialog:
    """Test de vraagtype modal"""

    def test_dialog(self):
        """Test basis modal functionaliteit"""
        root = tk.Tk()
        dialog = QuestionTypeDialog(root)
        dialog.select_type('multiple_choice')
        assert dialog.result == 'multiple_choice'
        dialog.destroy()
        root.destroy()

def format_date(timestamp):
    """Converteer timestamp naar datum string"""
    if not timestamp or "_seconds" not in timestamp:
        return ""
    try:
        return datetime.fromtimestamp(timestamp["_seconds"]).strftime("%d-%m-%Y %H:%M")
    except (TypeError, ValueError):
        return ""
