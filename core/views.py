# Django Imports
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.admin.views.decorators import staff_member_required
from django.core import serializers
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404

from .forms import InquiryForm, ReplyForm
from .models import Inquiry, Store
from .models import Store, Inquiry


# --- 認証関連ビュー ---
def admin_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            # 'admin' または 'store' ロールを持つユーザーのみログインを許可
            if user.role in ['admin', 'store']:
                login(request, user)
                return redirect('core:staff_index')
            else:
                form.add_error(None, "管理者または店舗アカウントでログインしてください。")
    # GETリクエストまたはフォームが無効な場合
    else:
        form = AuthenticationForm()
    return render(request, 'admin/staff_login.html', {'form': form})

# --- 一般ユーザー向けビュー ---

# トップ（最初の画面）


def index(request):
    if request.user.is_authenticated:
        return redirect('core:main_menu')
    return render(request, "core/index.html")


@login_required
def main_menu(request):
    user = request.user
    context = {
        'rank': user.rank,
        'current_points': user.current_points,
    }
    return render(request, "core/main_menu.html", context)


def coupon_list(request):
    return render(request, "core/coupon_list.html")


def store_map(request):
    stores = Store.objects.all()
    stores_json = serializers.serialize('json', stores)
    return render(request, 'core/store_map.html', {'stores_json': stores_json})


def result(request):
    return render(request, "core/result.html")


def scan(request):
    return render(request, "core/scan.html")


def ai_report(request):
    return render(request, "core/ai_report.html")


# --- 問い合わせ関連ビュー ---

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


# --- 店舗スタッフ向けビュー ---

@login_required
def store_help(request):
    return render(request, "admin/help.html")


# --- 管理者向けビュー ---

@staff_member_required
def admin_inquiry_dashboard(request):
    inquiries = Inquiry.objects.all().order_by('-id')
    context = {
        'inquiries': inquiries
    }
    return render(request, 'admin/inquiry_dashboard.html', context)


@staff_member_required
def inquiry_detail(request, inquiry_id):
    inquiry = get_object_or_404(Inquiry, id=inquiry_id)
    if request.method == 'POST':
        form = ReplyForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [inquiry.reply_to_email],
            )
            inquiry.is_replied = True
            inquiry.reply_message = message
            inquiry.save()
            # Redirect or show a success message
            return redirect('core:admin_inquiry_dashboard')
    else:
        form = ReplyForm(initial={'subject': f'Re: {inquiry.subject}'})

    context = {
        'inquiry': inquiry,
        'form': form
    }
    return render(request, 'admin/inquiry_detail.html', context)


@staff_member_required
def staff_index(request):
    return render(request, "admin/staff_index.html")

@staff_member_required
def store_list(request):
    stores = Store.objects.all()
    context = {
        'stores': stores,
    }
    return render(request, "admin/store_list.html", context)


@staff_member_required
def store_detail(request, store_id):
    store = get_object_or_404(Store, store_id=store_id)
    context = {
        'store': store
    }
    return render(request, 'admin/store_detail.html', context)

