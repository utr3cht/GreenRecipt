from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# メインメニュー
@login_required
def main_menu(request):
    user = request.user
    context = {
        'rank': user.rank,
        'current_points': user.current_points,
    }
    return render(request, "core/main_menu.html", context)

# トップ（最初の画面）
def index(request):
    return render(request, "core/index.html")

def coupon_list(request):
    return render(request, "core/coupon_list.html")

def store_map(request):
    return render(request, "core/store_map.html")

def result(request):
    return render(request, "core/result.html")

def scan(request):
    return render(request, "core/scan.html")

def ai_report(request):
    return render(request, "core/ai_report.html")

def inquiry(request):
    return render(request, "core/inquiry.html")

@login_required
def store_help(request):
    return render(request, "store_admin/help.html")