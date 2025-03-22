def filter_courses(profile, courses):
    preferences = profile.get("preferences", {})
    interests = preferences.get("interests", [])
    preferred_mode = preferences.get("learning_mode", "").lower()

    level = 0
    if profile.get("academic_background"):
        level = profile.get("academic_background", {}).get("highest_academic_level", 0)

    filtered = []
    for c in courses:
        if any(interest.lower() in c.get("titre", "").lower() for interest in interests):
            if c.get("niveau", 0) >= level:
                filtered.append(c)
    return filtered
