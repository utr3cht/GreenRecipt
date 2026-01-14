from django.shortcuts import redirect
from django.urls import reverse

class AdminAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # /admin/パスのみ対象
        if request.path.startswith('/admin/'):
            # 認証済みユーザー
            if request.user.is_authenticated:
                # 管理者/システムロール以外
                if not request.user.is_superuser and request.user.role not in ['admin', 'system']:
                    # indexへリダイレクト
                    return redirect('core:index')
        
        # 通常フローへ
        response = self.get_response(request)
        return response
