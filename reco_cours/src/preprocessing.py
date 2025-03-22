import json
import pandas as pd

def load_courses(path):
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    return data

def load_profiles(path):
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    return data if isinstance(data, list) else [data]

def flatten_course(course):
    flat = course['cours']
    flat['url'] = course.get('url')
    return flat

def preprocess_courses(courses):
    return [flatten_course(c) for c in courses]
