from sklearn.feature_extraction.text import TfidfVectorizer
from .models import Recommendation

class RecommendationEngine:
    def __init__(self):
        self.vectorizer = TfidfVectorizer()
    
    def generate_recommendations(self, user):
        # Logique de recommandation ici
        pass