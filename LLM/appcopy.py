import streamlit as st
import pandas as pd
import joblib
import numpy as np

# Chargement du modèle sauvegardé
model_details = joblib.load("best_model_rff.pkl")

model = model_details['model']
scaler = model_details['scaler']
label_encoder = model_details['label_encoder']
feature_mappings = model_details['feature_mappings']
features = model_details['features']

st.title("Prédiction du niveau d'expérience de l'étudiant")

# Interface utilisateur
age = st.number_input("Âge de l'étudiant", min_value=10, max_value=100, value=20)
gender = st.selectbox("Genre", ["M", "F"])
preferred_language = st.selectbox("Langue préférée", ["Python", "JavaScript", "Java", "SQL", "C++"])
learning_mode = st.selectbox("Mode d'apprentissage", ["En ligne", "Présentiel", "Alternance", "Hybride"])
highest_academic_level = st.selectbox("Niveau académique", ["Bac", "DUT", "Licence", "Master", "Ingénieur"])
total_experience_years = st.number_input("Années d'expérience", min_value=0.0, max_value=50.0, value=0.0, step=0.5)
fields_of_study = st.selectbox("Domaine d'étude", ["Informatique", "Marketing", "Gestion", "Finance", "Autre", "Bac S", "Génie Informatique", "Gestion des Entreprises"])

# Préparer les données d'entrée
input_data = pd.DataFrame({
    "age": [age],
    "gender": [feature_mappings['gender'][gender]],
    "preferred_language": [feature_mappings['preferred_language'][preferred_language]],
    "learning_mode": [feature_mappings['learning_mode'][learning_mode]],
    "highest_academic_level": [feature_mappings['highest_academic_level'][highest_academic_level]],
    "total_experience_years": [total_experience_years],
    "fields_of_study": [feature_mappings['fields_of_study'][fields_of_study]]
})

# Normaliser les données
input_scaled = scaler.transform(input_data[features])

# Prédiction
if st.button("Prédire le niveau"):
    prediction = model.predict(input_scaled)
    prediction_label = label_encoder.inverse_transform(prediction)[0]
    prediction_proba = model.predict_proba(input_scaled)[0]

    st.write(f"**Niveau prédit :** {prediction_label}")
    st.bar_chart(prediction_proba)
