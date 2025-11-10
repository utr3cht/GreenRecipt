# Django Imports
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.admin.views.decorators import staff_member_required
from django.core import serializers
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404

from .forms import InquiryForm, ReplyForm, AnnouncementForm
from .models import Inquiry, Store, Announcement
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib import messages
from accounts.models import CustomUser
from accounts.forms import StoreUserCreationForm
from .forms import InquiryForm, ReplyForm, StoreForm
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


def staff_logout(request):
    logout(request)
    return redirect('core:staff_login')


# --- 一般ユーザー向けビュー ---

# トップ（最初の画面）


def index(request):
    if request.user.is_authenticated:
        if request.user.role in ['admin', 'store']:
            return redirect('core:staff_index')
        else:
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
    stores_data = []
    for store in stores:
        stores_data.append({
            'store_name': store.store_name,
            'category': store.get_category_display(),
            'address': store.address,
            'tel': store.tel,
            'open_time': store.open_time,
            'close_time': store.close_time,
            'lat': store.lat,
            'lng': store.lng,
        })
    stores_json = json.dumps(stores_data, cls=DjangoJSONEncoder)
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


@login_required
def staff_inquiry(request):
    if request.user.role not in ['admin', 'store']:
        return redirect('core:index')

    if request.method == "POST":
        form = InquiryForm(request.POST, request.FILES)
        if form.is_valid():
            context = {"form": form}
            return render(request, "admin/staff_inquiry_confirm.html", context)
    else:
        form = InquiryForm()
        # もしユーザーが店舗スタッフなら、返信先メールアドレスを自動入力
        if request.user.role == 'store' and request.user.email:
            form.fields['reply_to_email'].initial = request.user.email

    context = {"form": form}
    return render(request, "admin/staff_inquiry.html", context)


@login_required
def staff_inquiry_create(request):
    if request.user.role not in ['admin', 'store']:
        return redirect('core:index')

    if request.method == "POST":
        form = InquiryForm(request.POST, request.FILES)
        if form.is_valid():
            inquiry = form.save(commit=False)
            inquiry.user = request.user
            inquiry.save()
            return redirect("core:staff_inquiry_complete")
    
    return redirect("core:staff_inquiry")


@login_required
def staff_inquiry_complete(request):
    if request.user.role not in ['admin', 'store']:
        return redirect('core:index')
    return render(request, "admin/staff_inquiry_complete.html")


# --- 管理者向けビュー ---

@staff_member_required
def announcement_list(request):
    if request.user.role != 'admin':
        return redirect('core:staff_index')
    announcements = Announcement.objects.all().order_by('-created_at')
    context = {'announcements': announcements}
    return render(request, 'admin/announcement_list.html', context)

@staff_member_required
def announcement_create(request):
    if request.user.role != 'admin':
        return redirect('core:staff_index')
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('core:announcement_list')
    else:
        form = AnnouncementForm()
    context = {'form': form}
    return render(request, 'admin/announcement_create.html', context)

@staff_member_required
def announcement_update(request, announcement_id):
    if request.user.role != 'admin':
        return redirect('core:staff_index')
    announcement = get_object_or_404(Announcement, pk=announcement_id)
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, request.FILES, instance=announcement)
        if form.is_valid():
            form.save()
            return redirect('core:announcement_list')
    else:
        form = AnnouncementForm(instance=announcement)
    context = {'form': form}
    return render(request, 'admin/announcement_update.html', context)

@staff_member_required
def announcement_delete(request, announcement_id):
    if request.user.role != 'admin':
        return redirect('core:staff_index')
    announcement = get_object_or_404(Announcement, pk=announcement_id)
    announcement.delete()
    return redirect('core:announcement_list')


@staff_member_required
def announcement_detail(request, announcement_id):
    if request.user.role not in ['admin', 'store']:
        return redirect('core:staff_index')
    
    announcement = get_object_or_404(Announcement, pk=announcement_id)
    context = {
        'announcement': announcement,
    }
    return render(request, 'admin/announcement_detail.html', context)


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


@login_required
def staff_index(request):
    if request.user.role not in ['admin', 'store']:
        return redirect('core:index')
    
    announcements = Announcement.objects.all().order_by('-created_at')
    context = {
        'announcements': announcements,
    }
    return render(request, "admin/staff_index.html", context)

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


@staff_member_required
def store_create(request):
    if request.method == 'POST':
        store_form = StoreForm(request.POST)
        user_form = StoreUserCreationForm(request.POST)
        if store_form.is_valid() and user_form.is_valid():
            store = store_form.save()
            user = user_form.save(commit=False)
            user.role = 'store'
            user.store = store
            user.is_staff = True
            user.save()
            messages.success(request, '店舗とアカウントが正常に登録されました。')
            return redirect('core:store_list')
    else:
        store_form = StoreForm()
        user_form = StoreUserCreationForm()
    return render(request, 'admin/store_create_form.html', {
        'store_form': store_form,
        'user_form': user_form
    })

@staff_member_required
def store_edit(request, store_id):
    store = get_object_or_404(Store, store_id=store_id)
    if request.method == 'POST':
        form = StoreForm(request.POST, instance=store)
        if form.is_valid():
            form.save()
            messages.success(request, '店舗情報が正常に更新されました。')
            return redirect('core:store_detail', store_id=store.store_id)
    else:
        form = StoreForm(instance=store)
    
    store_users = store.customuser_set.all()
    
    return render(request, 'admin/store_edit_form.html', {
        'form': form, 
        'store': store,
        'store_users': store_users
    })

@staff_member_required
def store_add_user(request, store_id):
    store = get_object_or_404(Store, store_id=store_id)
    if request.method == 'POST':
        form = StoreUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'store'
            user.store = store
            user.is_staff = True
            user.save()
            messages.success(request, '店舗アカウントが正常に登録されました。')
            return redirect('core:store_edit', store_id=store.store_id)
    else:
        form = StoreUserCreationForm()
    return render(request, 'admin/store_add_user.html', {'form': form, 'store': store})

@staff_member_required
def store_delete_user(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    store_id = user.store.store_id
    if request.method == 'POST':
        user.delete()
        messages.success(request, '店舗アカウントが正常に削除されました。')
        return redirect('core:store_edit', store_id=store_id)
    # It's better to not have a GET page for deletion, 
    # but for now, redirecting if accessed via GET.
    return redirect('core:store_edit', store_id=store_id)
