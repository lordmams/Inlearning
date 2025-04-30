# courses/urls.py
from django.urls import path
from .views import (
    DashboardView, CourseListView, CourseDetailView,
    EnrollCourseView, UnenrollCourseView,
    LessonDetailView, MarkLessonCompletedView
)

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('', CourseListView.as_view(), name='course_list'),
    path('<int:pk>/', CourseDetailView.as_view(), name='course_detail'),
    path('<int:pk>/enroll/', EnrollCourseView.as_view(), name='enroll_course'),
    path('<int:pk>/unenroll/', UnenrollCourseView.as_view(), name='unenroll_course'),
    path('lesson/<int:pk>/', LessonDetailView.as_view(), name='lesson_detail'),
    path('lesson/<int:lesson_pk>/complete/', MarkLessonCompletedView.as_view(), name='mark_lesson_completed'),
]