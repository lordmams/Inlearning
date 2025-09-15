import logging
import re
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class CourseProcessor:
    """Service de traitement et normalisation des données de cours"""
    
    def __init__(self):
        self.difficulty_mapping = {
            'débutant': 'beginner',
            'facile': 'beginner',
            'easy': 'beginner',
            'intermédiaire': 'intermediate',
            'moyen': 'intermediate',
            'medium': 'intermediate',
            'avancé': 'advanced',
            'difficile': 'advanced',
            'hard': 'advanced',
            'expert': 'advanced'
        }
        
        self.learning_mode_mapping = {
            'vidéo': 'video',
            'video': 'video',
            'texte': 'text',
            'text': 'text',
            'écrit': 'text',
            'pratique': 'practice',
            'practice': 'practice',
            'hands-on': 'practice',
            'exercice': 'practice'
        }
    
    def process_course(self, course_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite et normalise les données d'un cours
        
        Args:
            course_data: Données brutes du cours
            
        Returns:
            Données du cours traitées et normalisées
        """
        processed_data = course_data.copy()
        
        # Normaliser le titre
        processed_data['title'] = self._normalize_title(processed_data.get('title', ''))
        
        # Normaliser la description
        processed_data['description'] = self._normalize_description(processed_data.get('description', ''))
        
        # Normaliser la difficulté
        processed_data['difficulty'] = self._normalize_difficulty(processed_data.get('difficulty', 'beginner'))
        
        # Normaliser le mode d'apprentissage
        processed_data['learning_mode'] = self._normalize_learning_mode(processed_data.get('learning_mode', 'text'))
        
        # Normaliser l'instructeur
        processed_data['instructor'] = self._normalize_instructor(processed_data.get('instructor', ''))
        
        # Valider et normaliser la durée
        processed_data['duration'] = self._normalize_duration(processed_data.get('duration', 1))
        
        # Valider et normaliser le prix
        processed_data['price'] = self._normalize_price(processed_data.get('price', 0))
        
        # Traiter les leçons
        if 'lessons' in processed_data:
            processed_data['lessons'] = self._process_lessons(processed_data['lessons'])
        
        # Traiter les tags
        if 'tags' in processed_data:
            processed_data['tags'] = self._process_tags(processed_data['tags'])
        
        # Ajouter des métadonnées de traitement
        processed_data['processed_at'] = datetime.now().isoformat()
        processed_data['processor_version'] = '1.0'
        
        return processed_data
    
    def _normalize_title(self, title: str) -> str:
        """Normalise le titre du cours"""
        if not title:
            return "Cours sans titre"
        
        # Nettoyer et formater le titre
        title = title.strip()
        title = re.sub(r'\s+', ' ', title)  # Supprimer les espaces multiples
        title = title.title()  # Mettre en forme titre
        
        # Limiter la longueur
        if len(title) > 200:
            title = title[:197] + "..."
        
        return title
    
    def _normalize_description(self, description: str) -> str:
        """Normalise la description du cours"""
        if not description:
            return "Description non disponible"
        
        # Nettoyer la description
        description = description.strip()
        description = re.sub(r'\s+', ' ', description)
        
        # Supprimer les balises HTML basiques
        description = re.sub(r'<[^>]+>', '', description)
        
        # Limiter la longueur
        if len(description) > 1000:
            description = description[:997] + "..."
        
        return description
    
    def _normalize_difficulty(self, difficulty: str) -> str:
        """Normalise le niveau de difficulté"""
        if not difficulty:
            return 'beginner'
        
        difficulty_lower = difficulty.lower().strip()
        
        # Utiliser le mapping pour normaliser
        normalized = self.difficulty_mapping.get(difficulty_lower, difficulty_lower)
        
        # Vérifier que c'est une valeur valide
        if normalized not in ['beginner', 'intermediate', 'advanced']:
            return 'beginner'
        
        return normalized
    
    def _normalize_learning_mode(self, learning_mode: str) -> str:
        """Normalise le mode d'apprentissage"""
        if not learning_mode:
            return 'text'
        
        mode_lower = learning_mode.lower().strip()
        
        # Utiliser le mapping pour normaliser
        normalized = self.learning_mode_mapping.get(mode_lower, mode_lower)
        
        # Vérifier que c'est une valeur valide
        if normalized not in ['video', 'text', 'practice']:
            return 'text'
        
        return normalized
    
    def _normalize_instructor(self, instructor: str) -> str:
        """Normalise le nom de l'instructeur"""
        if not instructor:
            return "Instructeur non spécifié"
        
        # Nettoyer et formater le nom
        instructor = instructor.strip()
        instructor = re.sub(r'\s+', ' ', instructor)
        
        # Mettre en forme nom propre
        instructor = ' '.join(word.capitalize() for word in instructor.split())
        
        # Limiter la longueur
        if len(instructor) > 100:
            instructor = instructor[:97] + "..."
        
        return instructor
    
    def _normalize_duration(self, duration) -> int:
        """Normalise la durée du cours"""
        try:
            duration_int = int(float(duration)) if duration else 1
            
            # Limiter la durée entre 1 et 1000 heures
            if duration_int < 1:
                return 1
            elif duration_int > 1000:
                return 1000
            
            return duration_int
        except (ValueError, TypeError):
            return 1
    
    def _normalize_price(self, price) -> float:
        """Normalise le prix du cours"""
        try:
            price_float = float(price) if price else 0.0
            
            # Limiter le prix entre 0 et 10000
            if price_float < 0:
                return 0.0
            elif price_float > 10000:
                return 10000.0
            
            # Arrondir à 2 décimales
            return round(price_float, 2)
        except (ValueError, TypeError):
            return 0.0
    
    def _process_lessons(self, lessons: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Traite et normalise les leçons"""
        if not lessons:
            return []
        
        processed_lessons = []
        
        for i, lesson in enumerate(lessons):
            processed_lesson = {
                'title': self._normalize_lesson_title(lesson.get('title', f'Leçon {i+1}')),
                'content': self._normalize_lesson_content(lesson.get('content', '')),
                'order': lesson.get('order', i + 1),
                'video_url': self._normalize_video_url(lesson.get('video_url', ''))
            }
            processed_lessons.append(processed_lesson)
        
        # Trier par ordre
        processed_lessons.sort(key=lambda x: x['order'])
        
        return processed_lessons
    
    def _normalize_lesson_title(self, title: str) -> str:
        """Normalise le titre d'une leçon"""
        if not title:
            return "Leçon sans titre"
        
        title = title.strip()
        title = re.sub(r'\s+', ' ', title)
        
        # Limiter la longueur
        if len(title) > 200:
            title = title[:197] + "..."
        
        return title
    
    def _normalize_lesson_content(self, content: str) -> str:
        """Normalise le contenu d'une leçon"""
        if not content:
            return "Contenu de la leçon à définir"
        
        content = content.strip()
        
        # Nettoyer les balises HTML basiques mais garder la structure
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
        
        return content
    
    def _normalize_video_url(self, video_url: str) -> str:
        """Normalise l'URL de la vidéo"""
        if not video_url:
            return ""
        
        video_url = video_url.strip()
        
        # Vérifier que c'est une URL valide
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if url_pattern.match(video_url):
            return video_url
        else:
            logger.warning(f"URL vidéo invalide: {video_url}")
            return ""
    
    def _process_tags(self, tags: List[str]) -> List[str]:
        """Traite et normalise les tags"""
        if not tags:
            return []
        
        processed_tags = []
        
        for tag in tags:
            if isinstance(tag, str) and tag.strip():
                # Normaliser le tag
                normalized_tag = tag.strip().lower()
                normalized_tag = re.sub(r'[^\w\-]', '', normalized_tag)  # Garder seulement alphanumériques et tirets
                
                if normalized_tag and len(normalized_tag) <= 50:
                    processed_tags.append(normalized_tag)
        
        # Supprimer les doublons et limiter le nombre
        processed_tags = list(dict.fromkeys(processed_tags))[:10]
        
        return processed_tags
    
    def validate_course_data(self, course_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Valide les données d'un cours et retourne les erreurs/avertissements
        
        Args:
            course_data: Données du cours à valider
            
        Returns:
            Dictionnaire avec les erreurs et avertissements
        """
        errors = []
        warnings = []
        
        # Validation des champs obligatoires
        if not course_data.get('title'):
            errors.append("Le titre est obligatoire")
        
        if not course_data.get('description'):
            warnings.append("La description est recommandée")
        
        if not course_data.get('instructor'):
            warnings.append("Le nom de l'instructeur est recommandé")
        
        # Validation des valeurs
        duration = course_data.get('duration')
        if duration and (not isinstance(duration, (int, float)) or duration <= 0):
            errors.append("La durée doit être un nombre positif")
        
        price = course_data.get('price')
        if price and (not isinstance(price, (int, float)) or price < 0):
            errors.append("Le prix doit être un nombre positif ou zéro")
        
        # Validation des choix
        difficulty = course_data.get('difficulty')
        if difficulty and difficulty not in ['beginner', 'intermediate', 'advanced']:
            errors.append("La difficulté doit être 'beginner', 'intermediate' ou 'advanced'")
        
        learning_mode = course_data.get('learning_mode')
        if learning_mode and learning_mode not in ['video', 'text', 'practice']:
            errors.append("Le mode d'apprentissage doit être 'video', 'text' ou 'practice'")
        
        # Validation des leçons
        lessons = course_data.get('lessons', [])
        if lessons:
            for i, lesson in enumerate(lessons):
                if not lesson.get('title'):
                    warnings.append(f"Leçon {i+1}: titre manquant")
                
                if not lesson.get('content'):
                    warnings.append(f"Leçon {i+1}: contenu manquant")
        
        return {
            'errors': errors,
            'warnings': warnings,
            'is_valid': len(errors) == 0
        }
    
    def enrich_course_data(self, course_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrichit les données d'un cours avec des informations calculées
        
        Args:
            course_data: Données du cours à enrichir
            
        Returns:
            Données du cours enrichies
        """
        enriched_data = course_data.copy()
        
        # Calculer des métriques
        lessons = course_data.get('lessons', [])
        enriched_data['lessons_count'] = len(lessons)
        
        # Estimer la durée totale basée sur les leçons
        if lessons and not course_data.get('duration'):
            estimated_duration = max(1, len(lessons) * 0.5)  # 30 min par leçon
            enriched_data['duration'] = int(estimated_duration)
        
        # Générer un slug pour l'URL
        title = course_data.get('title', '')
        if title:
            slug = re.sub(r'[^\w\s-]', '', title.lower())
            slug = re.sub(r'[-\s]+', '-', slug)
            enriched_data['slug'] = slug[:50]
        
        # Calculer un score de qualité
        quality_score = self._calculate_quality_score(course_data)
        enriched_data['quality_score'] = quality_score
        
        # Ajouter des métadonnées
        enriched_data['enriched_at'] = datetime.now().isoformat()
        
        return enriched_data
    
    def _calculate_quality_score(self, course_data: Dict[str, Any]) -> float:
        """Calcule un score de qualité pour le cours"""
        score = 0.0
        
        # Score basé sur la présence de champs
        if course_data.get('title'):
            score += 20
        if course_data.get('description') and len(course_data['description']) > 50:
            score += 20
        if course_data.get('instructor'):
            score += 15
        if course_data.get('lessons'):
            score += 25
        if course_data.get('duration') and course_data['duration'] > 0:
            score += 10
        if course_data.get('tags'):
            score += 10
        
        return min(100.0, score) 