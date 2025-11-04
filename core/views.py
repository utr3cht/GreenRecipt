from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import InquiryForm
from .models import Inquiry

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
    if request.method == "POST":
        form = InquiryForm(request.POST, request.FILES)
        if form.is_valid():
            context = {"form": form}
            return render(request, "core/inquiry_confirm.html", context)
    else:
        form = InquiryForm()
    context = {"form": form}
    return render(request, "core/inquiry.html", context)


def inquiry_create(request):
    if request.method == "POST":
        form = InquiryForm(request.POST, request.FILES)
        if form.is_valid():
            inquiry = form.save(commit=False)
            if request.user.is_authenticated:
                inquiry.user = request.user
            inquiry.save()
            return redirect("core:inquiry_complete")
    # フォームが無効な場合やGETリクエストの場合は入力画面に戻す
    return redirect("core:inquiry")


def inquiry_complete(request):
    return render(request, "core/inquiry_complete.html")