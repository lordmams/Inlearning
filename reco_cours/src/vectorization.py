from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

def get_course_text(course):
    return f"{course.get('titre', '')}. {course.get('description', '')}"

def get_profile_text(profile):
    prefs = profile.get('preferences', {})
    goals = profile.get('goals', {})
    text = ' '.join(prefs.get('interests', []))
    text += ' ' + ' '.join(goals.get('short_term_goals', []))
    text += ' ' + ' '.join(goals.get('long_term_goals', []))
    return text

def vectorize_courses(courses):
    texts = [get_course_text(c) for c in courses]
    vectors = model.encode(texts)
    return vectors

def vectorize_profile(profile):
    text = get_profile_text(profile)
    return model.encode([text])[0]
