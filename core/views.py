# Django Imports
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.admin.views.decorators import staff_member_required
from django.core import serializers
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages # Added messages import
from django.core.files.storage import FileSystemStorage
from yomitoku.document_analyzer import DocumentAnalyzer
import cv2

# Forms
from .forms import InquiryForm, ReplyForm, StoreForm, AnnouncementForm

# Models
from .models import Inquiry, Store, Announcement, Receipt # Assuming Announcement model exists
from accounts.models import CustomUser # From accounts app

import json
from django.core.serializers.json import DjangoJSONEncoder


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


def receipt_detail(request, receipt_id):
    receipt = get_object_or_404(Receipt, pk=receipt_id, user=request.user)
    context = {
        'receipt': receipt,
    }
    return render(request, "core/result.html", context)

@login_required
def receipt_history(request):
    receipts = Receipt.objects.filter(user=request.user).order_by('-scanned_at')
    context = {
        'receipts': receipts,
    }
    return render(request, "core/receipt_history.html", context)


@login_required
def scan(request):
    if request.method == 'POST':
        image_file = request.FILES.get('receipt_image')
        if image_file:
            fs = FileSystemStorage()
            # ファイルを保存
            filename = fs.save('receipts/' + image_file.name, image_file)
            # 保存したファイルの絶対パスとURLを取得
            image_path = fs.path(filename)
            image_url = fs.url(filename)

            # yomitokuでOCR処理
            try:
                # DocumentAnalyzerのインスタンスを作成
                analyzer = DocumentAnalyzer()
                # 画像を読み込む
                img = cv2.imread(image_path)
                # 解析を実行
                results, _, _ = analyzer(img)
                
                # 結果からテキストを抽出
                ocr_text = ""
                if results and hasattr(results, 'paragraphs'):
                    for paragraph in results.paragraphs:
                        ocr_text += paragraph.contents + "\n"
                
                if not ocr_text:
                    ocr_text = "テキストが検出されませんでした。"

            except Exception as e:
                messages.error(request, f"OCR処理中にエラーが発生しました: {e}")
                return redirect('core:scan')

            # OCR結果をデータベースに保存
            receipt = Receipt.objects.create(
                user=request.user,
                image_url=image_url,
                ocr_text=ocr_text
            )
            
            messages.success(request, 'レシート画像が正常にアップロードされ、OCR処理が完了しました。')
            return redirect('core:receipt_detail', receipt_id=receipt.id)
        else:
            messages.error(request, '画像ファイルが選択されていません。')
            return redirect('core:scan')
            
    return render(request, "core/scan.html")


def ai_report(request):
    return render(request, "core/ai_report.html")


# --- 問い合わせ関連ビュー ---

def inquiry(request):
    if request.method == "POST":
        form = InquiryForm(request.POST, request.FILES)
        if form.is_valid():
            inquiry = form.save(commit=False)
            if request.user.is_authenticated:
                inquiry.user = request.user
            inquiry.save()
            return redirect("core:inquiry_complete")
    else:
        form = InquiryForm()
    context = {"form": form}
    return render(request, "core/inquiry.html", context)


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
            inquiry = form.save(commit=False)
            inquiry.user = request.user
            inquiry.save()
            return redirect("core:staff_inquiry_complete")
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
