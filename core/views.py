from django.shortcuts import render

# メインメニュー
def main_menu(request):
    return render(request, "core/main_menu.html")

# トップ（最初の画面）
def index(request):
    return render(request, "core/index.html")

# ログイン画面
def login_view(request):
    return render(request, "core/login.html")

# 新規登録画面
def register(request):
    return render(request, "core/register.html")

# 登録確認画面
def register_confirm(request):
    return render(request, "core/register_confirm.html")