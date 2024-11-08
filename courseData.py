# New file for configuration data
SUBJECTS_DATA = {
    "Onderdelen": ["Wetgeving", "Voorrang", "Gebruik van de weg", "Verkeersregels", "Verkeersveiligheid", "Gevaarherkenning"],
    "Examen": ["Examen 1: Gevaarherkenning", "Examen 1: Kennis", "Examen 1: Inzicht", 
               "Examen 2: Gevaarherkenning", "Examen 2: Kennis", "Examen 2: Inzicht",
               "Examen 3: Gevaarherkenning", "Examen 3: Kennis", "Examen 3: Inzicht"]
}

QUESTIONS_DATA = {
            "Wetgeving": [
                {
                    "question": "Wat doet u in deze situatie?",
                    "type": "multiple_choice",
                    "options": ["A: Remmen", "B: Gas los", "C: Niks", "D: Claxonneren"],
                    "correct": "A",
                    "explanation": "Remmen is hier het veiligst omdat er een gevaarlijke situatie ontstaat.",
                    "image": "https://example.com/image1.jpg"
                },
                 {
            "question": "Wat is de maximumsnelheid op deze weg?",
            "type": "open",
            "answer": 50,
            "unit": "KM/U",
            "explanation": "Binnen de bebouwde kom is de maximumsnelheid 50 km/u",
            "image": "https://www.researchgate.net/profile/Nicholas-Tran-3/publication/228923045/figure/fig1/AS:668988552007691@1536510708944/Test-images-left-to-right-in-pgm-format-original-watermarked-right-shifted.ppm"
        },
        {
            "question": "Welke situatie is het gevaarlijkst?",
            "type": "image_selection",
            "imageOptions": [
                "https://www.researchgate.net/profile/Nicholas-Tran-3/publication/228923045/figure/fig1/AS:668988552007691@1536510708944/Test-images-left-to-right-in-pgm-format-original-watermarked-right-shifted.ppm",
                "https://www.researchgate.net/profile/Nicholas-Tran-3/publication/228923045/figure/fig1/AS:668988552007691@1536510708944/Test-images-left-to-right-in-pgm-format-original-watermarked-right-shifted.ppm",
                "https://www.researchgate.net/profile/Nicholas-Tran-3/publication/228923045/figure/fig1/AS:668988552007691@1536510708944/Test-images-left-to-right-in-pgm-format-original-watermarked-right-shifted.ppm",
                "https://www.researchgate.net/profile/Nicholas-Tran-3/publication/228923045/figure/fig1/AS:668988552007691@1536510708944/Test-images-left-to-right-in-pgm-format-original-watermarked-right-shifted.ppm"
            ],
            "correctAnswer": 1,
            "explanation": "De tweede situatie is het gevaarlijkst vanwege beperkt zicht.",
            "image": ""
        }
            ],
            "Voorrang": [
                 {
            "question": "Wat doet u in deze situatie?",
            "type": "multiple_choice",
            "options": ["A: Remmen", "B: Gas los", "C: Niks", "D: Claxonneren"],
            "correct": "A",
            "explanation": "Remmen is hier het veiligst omdat er een gevaarlijke situatie ontstaat.",
            "image": "https://www.researchgate.net/profile/Nicholas-Tran-3/publication/228923045/figure/fig1/AS:668988552007691@1536510708944/Test-images-left-to-right-in-pgm-format-original-watermarked-right-shifted.ppm"
        },
        {
            "question": "Plaats de verkeersborden op de juiste locatie",
            "type": "drag_and_drop",
            "explanation": "De verkeersborden moeten op specifieke posities geplaatst worden voor optimale zichtbaarheid.",
            "correctPositions": [
                {"positionX": 50, "positionY": 100},
                {"positionX": 200, "positionY": 220},
                {"positionX": 300, "positionY": 100}
            ],
            "image": "https://www.researchgate.net/profile/Nicholas-Tran-3/publication/228923045/figure/fig1/AS:668988552007691@1536510708944/Test-images-left-to-right-in-pgm-format-original-watermarked-right-shifted.ppm"
        }
            ]
        }