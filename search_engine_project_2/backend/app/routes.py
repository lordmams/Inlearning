from flask import Blueprint, request, jsonify
from .recommendation import recommend_courses
from .utils import load_data

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return "Bienvenue sur l'API de recommandation de cours!"

@main_bp.route('/api/recommendations', methods=['POST'])
def get_recommendations():
    student_data = request.json
    courses, students = load_data()
    
    recommendations = recommend_courses(student_data, courses)
    
    return jsonify(recommendations)
