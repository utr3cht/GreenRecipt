from django.shortcuts import redirect
from django.urls import reverse

class AdminAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # We only care about paths starting with /admin/
        if request.path.startswith('/admin/'):
            # If the user is authenticated
            if request.user.is_authenticated:
                # And their role is not admin or system
                if not request.user.is_superuser and request.user.role not in ['admin', 'system']:
                    # Redirect them to the index page.
                    return redirect('core:index')
        
        # If the conditions are not met, continue with the normal flow
        response = self.get_response(request)
        return response
