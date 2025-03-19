from .vectorization import vectorize_courses
from sklearn.metrics.pairwise import cosine_similarity

# Recommandation des cours basée sur les préférences des étudiants
def recommend_courses(student_data, courses):
    # Vectorisation des descriptions des cours
    course_vectors = vectorize_courses(courses)
    
    # Exemple simplifié: la similitude entre les intérêts de l'étudiant et les cours
    student_interests = ' '.join(student_data['preferences']['interests'])
    student_vector = vectorize_courses([{'description': student_interests}])
    
    # Calcul de la similitude entre l'étudiant et les cours
    similarities = cosine_similarity(student_vector, course_vectors)
    
    # Récupérer les indices des cours recommandés
    recommended_indices = similarities.argsort()[0][-5:][::-1]  # Top 5 recommandations
    recommended_courses = [courses[i] for i in recommended_indices]
    
    return recommended_courses
