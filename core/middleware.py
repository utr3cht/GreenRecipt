from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from accounts.models import CustomUser

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


class MonthlyPointResetMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.role == 'user':
            today = timezone.now().date()
            # 月初めを取得 (1日)
            first_day_of_month = today.replace(day=1)
            
            if not request.user.last_reset_month:
                # 初回導入時：リセットせず、今月を「リセット済み」としてマーク
                user = request.user
                user.last_reset_month = first_day_of_month
                user.save()
            elif request.user.last_reset_month < first_day_of_month:
                # 実際に月が替わった場合：リセット実行
                user = request.user
                user.current_points = 0
                user.last_reset_month = first_day_of_month
                user.save()
        
        response = self.get_response(request)
        return response


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # 強制的に X-XSS-Protection を付与
        response['X-XSS-Protection'] = '1; mode=block'
        return response
