# courses/urls.py
from django.urls import path
from .views import (
    DashboardView, CourseListView, CourseDetailView,
    EnrollCourseView, UnenrollCourseView,
    LessonDetailView, MarkLessonCompletedView,
    CourseCreateView, CourseUpdateView, CourseDeleteView,
    GenerateLearningPathView, LearningPathDetailView
)

print("\n=== Loading Courses URLs ===")

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('', CourseListView.as_view(), name='course_list'),
    path('<int:pk>/', CourseDetailView.as_view(), name='course_detail'),
    path('<int:pk>/enroll/', EnrollCourseView.as_view(), name='enroll_course'),
    path('<int:pk>/unenroll/', UnenrollCourseView.as_view(), name='unenroll_course'),
    path('lesson/<int:pk>/', LessonDetailView.as_view(), name='lesson_detail'),
    path('lesson/<int:lesson_pk>/complete/', MarkLessonCompletedView.as_view(), name='mark_lesson_completed'),
    path('course/create/', CourseCreateView.as_view(), name='course_create'),
    path('course/<int:pk>/update/', CourseUpdateView.as_view(), name='course_update'),
    path('course/<int:pk>/delete/', CourseDeleteView.as_view(), name='course_delete'),
    path('generate-learning-path/', GenerateLearningPathView.as_view(), name='generate_learning_path'),
    path('learning-path/', LearningPathDetailView.as_view(), name='learning_path_detail'),
]

print("Courses URLs patterns:")
for pattern in urlpatterns:
    print(f"- {pattern.pattern} -> {pattern.name}")
print("=== Courses URLs loaded ===\n")