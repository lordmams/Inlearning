# Fonctions utilitaires, comme la gestion des données, des entrées ou des transformations
def load_data():
    import json
    with open('data/courses.json') as f:
        courses = json.load(f)
    with open('data/students.json') as f:
        students = json.load(f)
    return courses, students
