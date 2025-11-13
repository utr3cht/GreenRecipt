# Django Imports
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.admin.views.decorators import staff_member_required
from django.core import serializers
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from yomitoku.document_analyzer import DocumentAnalyzer
import cv2
import re
from datetime import datetime
import json
from django.core.serializers.json import DjangoJSONEncoder

# Forms
from .forms import InquiryForm, ReplyForm, StoreForm, AnnouncementForm

# Models
from .models import Inquiry, Store, Announcement, Receipt, Coupon
from accounts.models import CustomUser

# --- 認証関連ビュー ---
def admin_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.role in ['admin', 'store']:
                login(request, user)
                return redirect('core:staff_index')
            else:
                form.add_error(None, "管理者または店舗アカウントでログインしてください。")
    else:
        form = AuthenticationForm()
    return render(request, 'admin/staff_login.html', {'form': form})

def staff_logout(request):
    logout(request)
    return redirect('core:staff_login')

# --- 一般ユーザー向けビュー ---
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
    announcements = Announcement.objects.order_by('-created_at')[:3]
    coupons = Coupon.objects.all()[:3]
    receipts = Receipt.objects.filter(user=request.user).order_by('-scanned_at')[:3]
    context = {
        'announcements': announcements,
        'coupons': coupons,
        'receipts': receipts,
    }
    return render(request, "core/main_menu.html", context)

@login_required
def coupon_list(request):
    coupons = Coupon.objects.all()
    return render(request, "core/coupon_list.html", {'coupons': coupons})

@login_required
def store_map(request):
    stores = Store.objects.all()
    stores_json = serializers.serialize('json', stores)
    return render(request, 'core/store_map.html', {'stores_json': stores_json})

@login_required
def receipt_history(request):
    receipts = Receipt.objects.filter(user=request.user).order_by('-scanned_at')
    return render(request, "core/receipt_history.html", {'receipts': receipts})

@login_required
def receipt_detail(request, receipt_id):
    receipt = get_object_or_404(Receipt, pk=receipt_id, user=request.user)
    return render(request, "core/result.html", {'receipt': receipt})

def parse_receipt_data(text):
    """
    OCRテキストから店舗名、取引日時、商品リストを抽出する。
    様々なフォーマットに対応するため、複数の正規表現を試す。
    """
    lines = text.split('\n')
    
    # --- 店舗名の抽出 ---
    store_name = lines[0] if lines else "不明な店舗"

    # --- 取引日時の抽出 (より厳密な正規表現) ---
    transaction_time = None
    # パターン: 2025年11月12日(水)17:03 または 2025年10月 9日 12:51
    date_pattern = re.compile(r'(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日(?:\s*\(.\))?\s*(\d{1,2}):(\d{1,2})')
    for line in lines:
        match = date_pattern.search(line)
        if match:
            try:
                year, month, day, hour, minute = map(int, match.groups())
                transaction_time = datetime(year, month, day, hour, minute)
                break
            except (ValueError, IndexError):
                continue

    # --- 商品リストの抽出 ---
    items = []
    start_keywords = ['【領収証】', '領収証', '領収書', '内訳']
    end_keywords = ['小計', '合計', '点数', 'お会計']
    
    # パターン定義
    item_pattern = re.compile(r'^\d+\s+(.+?)\s*(?:[¥￥]|$)') # コード 商品名 ... (価格はあってもなくても良い)
    quantity_pattern = re.compile(r'\(?(\d+)\s*(?:個|点|x|X)\b')
    price_line_pattern = re.compile(r'^\s*[¥￥][\d,]+')
    exclude_keywords = ['【領収証】', '領収証', '領収書', '内訳', 'アクロスプラザ', '電話', 'コード', 'レジ', '責', 'No.']


    in_items_section = False
    last_item_added = None

    for i, line in enumerate(lines):
        line_no_space = line.replace(' ', '').replace('　', '')
        
        if not in_items_section and any(keyword in line_no_space for keyword in start_keywords):
            in_items_section = True
            continue
        
        if in_items_section and any(keyword in line for keyword in end_keywords):
            break

        if in_items_section:
            line = line.strip()
            if not line: continue

            # 個数行のチェックを先に行う
            if last_item_added:
                quantity_match = quantity_pattern.search(line)
                if quantity_match:
                    last_item_added['quantity'] = int(quantity_match.group(1))
                    continue # 個数行は処理したので次へ

            # 価格のみの行は無視
            if price_line_pattern.match(line):
                continue

            # 商品行の解析
            item_match = item_pattern.search(line)
            if item_match:
                name = item_match.group(1).strip()
                # 価格部分が商品名に含まれていたら削除
                name = re.sub(r'\s*[¥￥].*$', '', name).strip()
                
                item = {"name": name, "quantity": 1, "price": 0}
                items.append(item)
                last_item_added = item # 新しい商品を「最後のアイテム」として設定
                continue
            
            # 上記のいずれにも一致しないが、除外キーワードも含まない行を商品候補とする (LAWSON形式など)
            if not any(kw in line for kw in exclude_keywords) and not line.isdigit():
                 # ただし、前のループでitem_patternに一致するものが一つでもあれば、このロジックは実行しない
                if not any(item_pattern.search(i['name']) for i in items):
                    items.append({"name": line, "quantity": 1, "price": 0})


    return {
        "store_name": store_name,
        "transaction_time": transaction_time,
        "items": items
    }

@login_required
def scan(request):
    if request.method == 'POST':
        image_file = request.FILES.get('receipt_image')
        if image_file:
            fs = FileSystemStorage()
            filename = fs.save('receipts/' + image_file.name, image_file)
            image_path = fs.path(filename)
            image_url = fs.url(filename)
            try:
                analyzer = DocumentAnalyzer()
                img = cv2.imread(image_path)
                results, _, _ = analyzer(img)
                ocr_text = "".join(paragraph.contents + "\n" for paragraph in results.paragraphs) if results and hasattr(results, 'paragraphs') else "テキストが検出されませんでした。"
            except Exception as e:
                messages.error(request, f"OCR処理中にエラーが発生しました: {e}")
                return redirect('core:scan')
            
            parsed_data = parse_receipt_data(ocr_text)
            store = None
            if parsed_data['store_name']:
                try:
                    store = Store.objects.filter(store_name__icontains=parsed_data['store_name'].strip()).first()
                except Exception:
                    pass
            
            receipt = Receipt.objects.create(
                user=request.user,
                image_url=image_url,
                ocr_text=ocr_text,
                store=store,
                transaction_time=parsed_data['transaction_time'],
                parsed_data=parsed_data['items']
            )
            messages.success(request, 'レシートが正常に解析されました。')
            return redirect('core:receipt_detail', receipt_id=receipt.id)
        else:
            messages.error(request, '画像ファイルが選択されていません。')
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
    return render(request, "core/inquiry.html", {"form": form})

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
        if request.user.role == 'store' and request.user.email:
            form.fields['reply_to_email'].initial = request.user.email
    return render(request, "admin/staff_inquiry.html", {"form": form})

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
    announcements = Announcement.objects.all().order_by('-created_at')
    return render(request, 'admin/announcement_list.html', {'announcements': announcements})

@staff_member_required
def announcement_create(request):
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('core:announcement_list')
    else:
        form = AnnouncementForm()
    return render(request, 'admin/announcement_create.html', {'form': form})

@staff_member_required
def announcement_update(request, announcement_id):
    announcement = get_object_or_404(Announcement, pk=announcement_id)
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, request.FILES, instance=announcement)
        if form.is_valid():
            form.save()
            return redirect('core:announcement_list')
    else:
        form = AnnouncementForm(instance=announcement)
    return render(request, 'admin/announcement_update.html', {'form': form})

@staff_member_required
def announcement_delete(request, announcement_id):
    announcement = get_object_or_404(Announcement, pk=announcement_id)
    announcement.delete()
    return redirect('core:announcement_list')

@staff_member_required
def announcement_detail(request, announcement_id):
    announcement = get_object_or_404(Announcement, pk=announcement_id)
    return render(request, 'admin/announcement_detail.html', {'announcement': announcement})

@staff_member_required
def admin_inquiry_dashboard(request):
    inquiries = Inquiry.objects.all().order_by('-id')
    return render(request, 'admin/inquiry_dashboard.html', {'inquiries': inquiries})

@staff_member_required
def inquiry_detail(request, inquiry_id):
    inquiry = get_object_or_404(Inquiry, id=inquiry_id)
    if request.method == 'POST':
        form = ReplyForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [inquiry.reply_to_email])
            inquiry.is_replied = True
            inquiry.reply_message = message
            inquiry.save()
            return redirect('core:admin_inquiry_dashboard')
    else:
        form = ReplyForm(initial={'subject': f'Re: {inquiry.subject}'})
    return render(request, 'admin/inquiry_detail.html', {'inquiry': inquiry, 'form': form})

@login_required
def staff_index(request):
    announcements = Announcement.objects.all().order_by('-created_at')
    return render(request, "admin/staff_index.html", {'announcements': announcements})

@staff_member_required
def store_list(request):
    stores = Store.objects.all()
    return render(request, "admin/store_list.html", {'stores': stores})

@staff_member_required
def store_detail(request, store_id):
    store = get_object_or_404(Store, store_id=store_id)
    return render(request, 'admin/store_detail.html', {'store': store})

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
    return render(request, 'admin/store_create_form.html', {'store_form': store_form, 'user_form': user_form})

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
    return render(request, 'admin/store_edit_form.html', {'form': form, 'store': store, 'store_users': store_users})

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
    return redirect('core:store_edit', store_id=store_id)