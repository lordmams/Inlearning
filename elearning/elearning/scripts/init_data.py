# scripts/init_data.py
import os
import django
import random
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import timedelta

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elearning.elearning.settings')
django.setup()

from courses.models import Category, Course, Lesson, Enrollment
from users.models import Person, Preferences, Interest, AcademicBackground, FieldOfStudy, ProfessionalBackground, Job, Goals, ShortTermGoal, LongTermGoal

def create_categories():
    categories = [
        {
            'name': 'Programmation',
            'description': 'Cours de programmation pour tous les niveaux',
            'icon': 'bi-code-slash'
        },
        {
            'name': 'Langues',
            'description': 'Apprenez de nouvelles langues',
            'icon': 'bi-globe'
        },
        {
            'name': 'Business',
            'description': 'Développez vos compétences en affaires',
            'icon': 'bi-briefcase'
        },
        {
            'name': 'Design',
            'description': 'Cours de design graphique et web',
            'icon': 'bi-palette'
        },
        {
            'name': 'Data Science',
            'description': 'Analyse de données et intelligence artificielle',
            'icon': 'bi-graph-up'
        },
    ]
    
    created_categories = []
    for category_data in categories:
        category, created = Category.objects.get_or_create(
            name=category_data['name'],
            defaults={
                'description': category_data['description'],
                'icon': category_data['icon']
            }
        )
        created_categories.append(category)
    
    return created_categories

def create_courses(categories):
    courses_data = [
        {
            'title': 'Python pour débutants',
            'description': 'Apprenez les bases du langage Python, de la syntaxe aux structures de données.',
            'category': 'Programmation',
            'instructor': 'Jean Dupont',
            'duration': 30,
            'difficulty': 'beginner',
            'price': 0.00,
            'is_free': True,
            'learning_mode': 'video'
        },
        {
            'title': 'JavaScript avancé',
            'description': 'Maîtrisez les concepts avancés de JavaScript: closures, prototypes, async/await...',
            'category': 'Programmation',
            'instructor': 'Sophie Martin',
            'duration': 25,
            'difficulty': 'advanced',
            'price': 49.99,
            'is_free': False,
            'learning_mode': 'practice'
        },
        {
            'title': 'Anglais pour les affaires',
            'description': 'Développez votre vocabulaire professionnel et améliorez votre communication en entreprise.',
            'category': 'Langues',
            'instructor': 'John Smith',
            'duration': 40,
            'difficulty': 'intermediate',
            'price': 29.99,
            'is_free': False,
            'learning_mode': 'text'
        },
        {
            'title': 'Introduction au marketing digital',
            'description': 'Découvrez les fondamentaux du marketing en ligne et des médias sociaux.',
            'category': 'Business',
            'instructor': 'Marie Leroy',
            'duration': 20,
            'difficulty': 'beginner',
            'price': 0.00,
            'is_free': True,
            'learning_mode': 'video'
        },
        {
            'title': 'Design UI/UX moderne',
            'description': 'Créez des interfaces utilisateur intuitives et esthétiques pour le web et mobile.',
            'category': 'Design',
            'instructor': 'Alexandre Petit',
            'duration': 35,
            'difficulty': 'intermediate',
            'price': 59.99,
            'is_free': False,
            'learning_mode': 'practice'
        },
        {
            'title': 'Machine Learning avec Python',
            'description': 'Implémentez des algorithmes d\'apprentissage automatique avec scikit-learn et TensorFlow.',
            'category': 'Data Science',
            'instructor': 'Claire Dubois',
            'duration': 45,
            'difficulty': 'advanced',
            'price': 69.99,
            'is_free': False,
            'learning_mode': 'practice'
        },
        {
            'title': 'HTML & CSS pour débutants',
            'description': 'Créez vos premières pages web avec HTML et CSS.',
            'category': 'Programmation',
            'instructor': 'Paul Durant',
            'duration': 15,
            'difficulty': 'beginner',
            'price': 0.00,
            'is_free': True,
            'learning_mode': 'video'
        },
        {
            'title': 'Espagnol débutant',
            'description': 'Apprenez les bases de l\'espagnol: vocabulaire, grammaire et prononciation.',
            'category': 'Langues',
            'instructor': 'Carmen Rodriguez',
            'duration': 30,
            'difficulty': 'beginner',
            'price': 19.99,
            'is_free': False,
            'learning_mode': 'text'
        },
    ]
    
    created_courses = []
    
    # Map category names to objects
    category_map = {category.name: category for category in categories}
    
    for course_data in courses_data:
        category_name = course_data.pop('category')
        category = category_map.get(category_name)
        
        if category:
            course, created = Course.objects.get_or_create(
                title=course_data['title'],
                category=category,
                defaults=course_data
            )
            created_courses.append(course)
    
    return created_courses

def create_lessons(courses):
    for course in courses:
        # Create between 5 and 10 lessons for each course
        num_lessons = random.randint(5, 10)
        for i in range(1, num_lessons + 1):
            Lesson.objects.get_or_create(
                course=course,
                order=i,
                defaults={
                    'title': f'Leçon {i}: {random.choice(["Introduction", "Concepts de base", "Pratique", "Exercices", "Étude de cas", "Projet", "Révision"])}',
                    'content': f'Contenu de la leçon {i} pour le cours "{course.title}". Cette leçon couvre les aspects importants de ce sujet.'
                }
            )

def create_admin_user():
    # Create a superuser
    admin_username = 'admin'
    admin_email = 'admin@example.com'
    admin_password = 'adminpassword'
    
    try:
        admin_user = User.objects.get(username=admin_username)
        print(f'Admin user "{admin_username}" already exists')
    except User.DoesNotExist:
        admin_user = User.objects.create_superuser(
            username=admin_username,
            email=admin_email,
            password=admin_password,
            first_name='Admin',
            last_name='User'
        )
        print(f'Created admin user: {admin_username} / {admin_password}')
    
    return admin_user

def create_demo_user():
    # Create a regular demo user
    demo_username = 'demo'
    demo_email = 'demo@example.com'
    demo_password = 'demopassword'
    
    try:
        demo_user = User.objects.get(username=demo_username)
        print(f'Demo user "{demo_username}" already exists')
    except User.DoesNotExist:
        demo_user = User.objects.create_user(
            username=demo_username,
            email=demo_email,
            password=demo_password,
            first_name='Demo',
            last_name='User'
        )
        print(f'Created demo user: {demo_username} / {demo_password}')
    
    # Create a profile for the demo user
    try:
        person = Person.objects.get(user=demo_user)
        print(f'Profile for demo user already exists')
    except Person.DoesNotExist:
        person = Person.objects.create(
            user=demo_user,
            name='Demo User',
            age=30,
            gender='M',
            email=demo_email,
            phone='0123456789'
        )
        
        # Create preferences
        preferences = Preferences.objects.create(
            person=person,
            preferred_language='fr',
            learning_mode='video'
        )
        
        # Create interests
        interests = ['Programmation', 'Web', 'Mobile', 'Data Science']
        for interest_name in interests:
            Interest.objects.create(
                preferences=preferences,
                name=interest_name
            )
        
        # Create academic background
        academic = AcademicBackground.objects.create(
            person=person,
            highest_academic_level='master'
        )
        
        # Create field of study
        FieldOfStudy.objects.create(
            academic_background=academic,
            field_name='Informatique',
            institution='Université de Lyon',
            year_of_completion=2018
        )
        
        # Create professional background
        professional = ProfessionalBackground.objects.create(
            person=person,
            total_experience_years=5
        )
        
        # Create job history
        Job.objects.create(
            professional_background=professional,
            position='Développeur Web',
            company='TechCorp',
            start_date=timezone.now().date() - timedelta(days=365*3),
            end_date=timezone.now().date() - timedelta(days=365),
            is_current=False,
            description='Développement de sites web et d\'applications web avec Django et React.'
        )
        
        Job.objects.create(
            professional_background=professional,
            position='Lead Developer',
            company='InnovApp',
            start_date=timezone.now().date() - timedelta(days=365),
            end_date=None,
            is_current=True,
            description='Responsable de l\'équipe de développement et de l\'architecture technique des projets.'
        )
        
        # Create goals
        goals = Goals.objects.create(
            person=person
        )
        
        # Create short term goals
        short_term_goals = ['Apprendre React Native', 'Améliorer mes compétences en TDD']
        for goal_desc in short_term_goals:
            ShortTermGoal.objects.create(
                goals=goals,
                description=goal_desc
            )
        
        # Create long term goals
        long_term_goals = ['Devenir CTO', 'Lancer ma startup']
        for goal_desc in long_term_goals:
            LongTermGoal.objects.create(
                goals=goals,
                description=goal_desc
            )
        
        print('Created complete profile for demo user')
    
    return demo_user

def enroll_demo_user(user, courses):
    # Enroll the demo user in some courses with different progress states
    enrollment_data = [
        {'course_title': 'Python pour débutants', 'progress': 75, 'completed': False},
        {'course_title': 'HTML & CSS pour débutants', 'progress': 100, 'completed': True},
        {'course_title': 'Introduction au marketing digital', 'progress': 30, 'completed': False},
    ]
    
    course_map = {course.title: course for course in courses}
    
    for data in enrollment_data:
        course = course_map.get(data['course_title'])
        if course:
            enrollment, created = Enrollment.objects.get_or_create(
                user=user,
                course=course,
                defaults={
                    'progress': data['progress'],
                    'completed': data['completed']
                }
            )
            if created:
                print(f'Enrolled demo user in course: {course.title}')
            else:
                print(f'Demo user already enrolled in course: {course.title}')

def run():
    print('Initializing database with test data...')
    
    # Create categories
    print('Creating categories...')
    categories = create_categories()
    
    # Create courses
    print('Creating courses...')
    courses = create_courses(categories)
    
    # Create lessons
    print('Creating lessons...')
    create_lessons(courses)
    
    # Create admin user
    print('Creating admin user...')
    admin_user = create_admin_user()
    
    # Create demo user
    print('Creating demo user with complete profile...')
    demo_user = create_demo_user()
    
    # Enroll demo user in courses
    print('Enrolling demo user in courses...')
    enroll_demo_user(demo_user, courses)
    
    print('Done! You can now access the e-learning platform.')
    print('Admin credentials: admin / adminpassword')
    print('Demo credentials: demo / demopassword')

if __name__ == '__main__':
    run()