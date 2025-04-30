# elearning/elearning/middleware.py
import logging
from django.urls import resolve
from django.conf import settings

logger = logging.getLogger(__name__)

class URLDebugMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.DEBUG:
            current_url = request.path_info
            print("\n=== URL Debug Info ===")
            print(f"Requested URL: {current_url}")
            
            try:
                resolved_url = resolve(current_url)
                print(f"URL Name: {resolved_url.url_name}")
                print(f"View Function: {resolved_url.func.__name__}")
                print(f"URL Pattern: {resolved_url.route}")
                print(f"URL Arguments: {resolved_url.args}")
                print(f"URL Kwargs: {resolved_url.kwargs}")
                print(f"URL Namespace: {resolved_url.namespace}")
                print(f"App Name: {resolved_url.app_name}")
            except Exception as e:
                print(f"URL Resolution Error: {str(e)}")
            
            print("=== End URL Debug ===\n")

        response = self.get_response(request)
        return response