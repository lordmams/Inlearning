import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
import joblib

# Charger les données
data = pd.read_csv('generated_student_data_100k_final.csv')

# Nouvelle définition claire des catégories
def create_rank_category(years):
    if years == 0:
        return 'Débutant'
    elif 0 < years <= 2:
        return 'Junior'
    elif 2 < years <= 5:
        return 'Intermédiaire'
    elif 5 < years <= 10:
        return 'Senior'
    else:
        return 'Expert'

data['rank'] = data['total_experience_years'].apply(create_rank_category)

# Mapping des variables
mapping_dicts = {
    'gender': {"M": 0, "F": 1},
    'learning_mode': {"En ligne": 0, "Présentiel": 1, "Alternance": 2, "Hybride": 3},
    'highest_academic_level': {"Bac": 0, "DUT": 1, "Licence": 2, "Master": 3, "Ingénieur": 4},
    'preferred_language': {"Python": 0, "JavaScript": 1, "Java": 2, "SQL": 3, "C++": 4},
    'fields_of_study': {
        "Informatique": 0, "Marketing": 1, "Gestion": 2,
        "Finance": 3, "Autre": 4, "Bac S": 5,
        "Génie Informatique": 6, "Gestion des Entreprises": 7
    }
}

# Préparation des données
for col, mapping in mapping_dicts.items():
    data[col] = data[col].map(mapping)

data.dropna(subset=mapping_dicts.keys(), inplace=True)

le_target = LabelEncoder()
data['rank_encoded'] = le_target.fit_transform(data['rank'])

X = data[['age', 'gender', 'preferred_language', 'learning_mode',
          'highest_academic_level', 'total_experience_years', 'fields_of_study']]
y = data['rank_encoded']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Entraînement du modèle
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train_scaled, y_train)

# Sauvegarde du modèle
joblib.dump({
    'model': model,
    'scaler': scaler,
    'label_encoder': le_target,
    'feature_mappings': mapping_dicts,
    'features': X.columns.tolist()
}, 'best_model_rff.pkl')


