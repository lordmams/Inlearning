import streamlit as st
import pandas as pd
import joblib
import openai
import pdfplumber
import json

# === CONFIGURATION API GROQ ===
openai.api_key = "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"  # Mets ta vraie clé Groq ici
openai.api_base = "https://api.groq.com/openai/v1"

# === CHARGEMENT DU MODÈLE ===
model_details = joblib.load("best_model_rff.pkl")
model = model_details["model"]
scaler = model_details["scaler"]
label_encoder = model_details["label_encoder"]
feature_mappings = model_details["feature_mappings"]
features = model_details["features"]


# === ANALYSE DU CV PAR L'IA ===
def extract_cv_info_from_pdf(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        cv_text = "\n".join([page.extract_text() or "" for page in pdf.pages])
    cv_text = cv_text[:8000]

    prompt = f"""
Analyse ce CV et retourne ces informations sous forme de JSON :
- âge (si connu)
- email
- téléphone
- niveau académique (Bac, DUT, Licence, Master, Ingénieur)
- années d'expérience
- domaine d'étude (Informatique, Marketing, etc.)
- langage préféré
- mode d'apprentissage (En ligne, Présentiel, Alternance, Hybride)
- genre (M ou F)
Voici le texte :
\"\"\"
{cv_text}
\"\"\"
    """

    response = openai.ChatCompletion.create(
        model="llama3-8b-8192",
        messages=[
            {"role": "system", "content": "Tu es un assistant RH."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    content = response["choices"][0]["message"]["content"].strip()
    st.subheader("📦 Réponse brute de Groq (pour debug)")
    st.code(content, language="markdown")

    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Le modèle n’a pas retourné un JSON valide. Détail : {e}")


def safe_index(lst, value):
    try:
        return lst.index(value)
    except:
        return None


# === INTERFACE ===
st.title("🤖 Prédiction du niveau d'expérience via CV ou formulaire")

uploaded_cv = st.file_uploader("📄 Uploader un CV PDF", type=["pdf"])
cv_data = {}

if uploaded_cv and st.button("Analyser le CV avec l'IA"):
    with st.spinner("Analyse du CV en cours..."):
        try:
            cv_data = extract_cv_info_from_pdf(uploaded_cv)

            translations = {
                "academic_level": "niveau académique",
                "years_of_experience": "années d'expérience",
                "domain_of_study": "domaine d'étude",
                "preferred_language": "langage préféré",
                "learning_mode": "mode d'apprentissage",
            }
            for src, dest in translations.items():
                if src in cv_data:
                    cv_data[dest] = cv_data[src]

            normalisation = {
                "niveau académique": {
                    "Master 2": "Master",
                    "Master 1": "Master",
                    "Licence 3": "Licence",
                    "Licence 2": "Licence",
                    "DUT 2": "DUT",
                    "Baccalauréat": "Bac",
                },
                "domaine d'étude": {
                    "Data Engineer": "Informatique",
                    "Computer Science": "Informatique",
                    "Business": "Gestion",
                },
            }
            for field, mapping in normalisation.items():
                if field in cv_data and cv_data[field] in mapping:
                    cv_data[field] = mapping[cv_data[field]]

            st.success("✅ Analyse réussie !")
        except Exception as e:
            st.error(f"❌ Erreur : {e}")
            cv_data = {}

st.subheader("📝 Complète ou modifie les champs si besoin :")

# === FORMULAIRE ===
age = st.number_input(
    "Âge",
    min_value=10,
    max_value=100,
    value=int(cv_data["âge"]) if "âge" in cv_data and cv_data["âge"] else None,
)

gender_options = list(feature_mappings["gender"].keys())
gender = st.selectbox(
    "Genre", gender_options, index=safe_index(gender_options, cv_data.get("genre")) or 0
)

lang_options = list(feature_mappings["preferred_language"].keys())
preferred_language = st.selectbox(
    "Langage préféré",
    lang_options,
    index=safe_index(lang_options, cv_data.get("langage préféré")) or 0,
)

mode_options = list(feature_mappings["learning_mode"].keys())
learning_mode = st.selectbox(
    "Mode d'apprentissage",
    mode_options,
    index=safe_index(mode_options, cv_data.get("mode d'apprentissage")) or 0,
)

level_options = list(feature_mappings["highest_academic_level"].keys())
highest_academic_level = st.selectbox(
    "Niveau académique",
    level_options,
    index=safe_index(level_options, cv_data.get("niveau académique")) or 0,
)

total_experience_years = st.number_input(
    "Années d'expérience",
    min_value=0.0,
    max_value=50.0,
    value=float(cv_data.get("années d'expérience") or 0.0),
    step=0.5,
)

field_options = list(feature_mappings["fields_of_study"].keys())
fields_of_study = st.selectbox(
    "Domaine d'étude",
    field_options,
    index=safe_index(field_options, cv_data.get("domaine d'étude")) or 0,
)

# === PRÉDICTION ===
if st.button("🔮 Prédire le niveau d'expérience"):
    if not all(
        [
            age,
            gender,
            preferred_language,
            learning_mode,
            highest_academic_level,
            total_experience_years,
            fields_of_study,
        ]
    ):
        st.warning("⚠️ Merci de remplir tous les champs pour lancer la prédiction.")
    else:
        input_data = pd.DataFrame(
            {
                "age": [age],
                "gender": [feature_mappings["gender"][gender]],
                "preferred_language": [
                    feature_mappings["preferred_language"][preferred_language]
                ],
                "learning_mode": [feature_mappings["learning_mode"][learning_mode]],
                "highest_academic_level": [
                    feature_mappings["highest_academic_level"][highest_academic_level]
                ],
                "total_experience_years": [total_experience_years],
                "fields_of_study": [
                    feature_mappings["fields_of_study"][fields_of_study]
                ],
            }
        )

        input_scaled = scaler.transform(input_data[features])
        prediction = model.predict(input_scaled)
        prediction_label = label_encoder.inverse_transform(prediction)[0]
        prediction_proba = model.predict_proba(input_scaled)[0]

        st.success(f"🧠 Niveau estimé : **{prediction_label}**")
        st.bar_chart(prediction_proba)
