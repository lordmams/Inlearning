from flask import Blueprint, jsonify
import os
import sys
from pathlib import Path

# Ajouter le chemin des services
sys.path.append(str(Path(__file__).parent.parent))

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """Endpoint de santé pour le consumer"""
    try:
        # Vérifier l'état du consumer
        from services.course_consumer import CourseConsumer
        
        # Créer une instance temporaire pour obtenir le statut
        consumer = CourseConsumer()
        status = consumer.get_status()
        
        return jsonify({
            'status': 'healthy',
            'service': 'course_consumer',
            'consumer_status': status,
            'timestamp': status.get('last_check')
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'service': 'course_consumer',
            'error': str(e)
        }), 500

@health_bp.route('/consumer/status', methods=['GET'])
def consumer_status():
    """Statut détaillé du consumer"""
    try:
        from services.course_consumer import CourseConsumer
        
        consumer = CourseConsumer()
        status = consumer.get_status()
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'running': False
        }), 500 