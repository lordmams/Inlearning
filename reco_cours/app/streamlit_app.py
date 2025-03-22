import streamlit as st
import json

from src.recommender import recommend_courses
from src.preprocessing import load_courses, preprocess_courses

# 📦 Charger les données
@st.cache_data
def load_data():
    courses = load_courses("data/merged_courses_cleaned.json")
    return preprocess_courses(courses)

courses = load_data()

# 🧠 Interface utilisateur
st.set_page_config(page_title="Recommandation de Cours", layout="wide")
st.title("🎓 Générateur de Parcours Personnalisé")

# 📄 Formulaire
with st.form("student_form"):
    name = st.text_input("Nom complet")
    email = st.text_input("Adresse email")
    interests = st.multiselect("Thèmes d'apprentissage", ["Python", "JavaScript", "PHP", "React", "Data Science"])
    level = st.selectbox("Niveau académique", ["1", "2", "3", "4", "5"])
    mode = st.selectbox("Mode d'apprentissage préféré", ["en ligne", "présentiel", "mixte"])
    goals = st.text_area("Objectifs personnels (court et long terme)", height=100)
    submitted = st.form_submit_button("Générer les recommandations")

# 🚀 Si l’utilisateur soumet le formulaire
if submitted and interests:
    # Créer un faux profil structuré
    student_profile = {
        "person": {
            "name": name,
            "contact": {"email": email}
        },
        "preferences": {
            "preferred_language": "français",
            "learning_mode": mode,
            "interests": interests
        },
        "academic_background": {
            "highest_academic_level": int(level),
            "fields_of_study": []
        },
        "professional_background": {
            "total_experience_years": 0,
            "jobs": []
        },
        "goals": {
            "short_term_goals": [goals],
            "long_term_goals": [goals]
        }
    }

    recommended = recommend_courses(student_profile, courses, top_k=5)

    if recommended:
        st.subheader("📚 Cours recommandés :")
        for course in recommended:
            with st.expander(course["titre"]):
                st.markdown(f"**Durée** : {course.get('duree', 'non spécifiée')}")
                st.markdown(f"**Niveau** : {course.get('niveau', 'non spécifié')}")
                st.markdown(course.get("description", ""))
                st.markdown(f"[Lien vers le cours]({course.get('lien')})")
    else:
        st.warning("Aucun cours ne correspond exactement à votre profil. Essayez de modifier vos choix.")

elif submitted and not interests:
    st.error("⚠️ Veuillez sélectionner au moins un thème.")
