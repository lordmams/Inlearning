import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


def compute_similarity(profile_vector, course_vectors):
    sims = cosine_similarity([profile_vector], course_vectors)[0]
    return sims
