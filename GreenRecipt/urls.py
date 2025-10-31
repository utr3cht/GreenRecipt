from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from core import views

urlpatterns = [
    # ---- 各画面のURL設定 ----
    path("", views.index, name="index"),                        # トップ（index.html）
    path("login/", views.login_view, name="login"),              # ログイン
    path("register/", views.register, name="register"),          # 新規登録
    path("register/confirm/", views.register_confirm, name="register_confirm"),  # 登録確認
    path("menu/", views.main_menu, name="main_menu"),            # メインメニュー

    # ---- 管理画面 ----
    path("admin/", admin.site.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
