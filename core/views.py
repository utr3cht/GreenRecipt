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
from django.http import JsonResponse
from django.urls import reverse
from yomitoku.document_analyzer import DocumentAnalyzer
import cv2
import re
from datetime import datetime
import json
from django.core.serializers.json import DjangoJSONEncoder
import requests  # Add this import
from django.core.files.base import ContentFile  # fs.saveエラーを修正するために追加

# Forms
from .forms import InquiryForm, ReplyForm, StoreForm, AnnouncementForm
# ⭐️ 修正: StoreUserCreationForm は accounts.forms からインポート
from accounts.forms import StoreUserCreationForm

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
    receipts = Receipt.objects.filter(
        user=request.user).order_by('-scanned_at')[:3]
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
    receipts = Receipt.objects.filter(
        user=request.user).order_by('-scanned_at')
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

    # --- 店舗名の抽出 (新ロジック) ---
    store_name = "不明"
    # レシートの上部から数行をチェック
    for line in lines[:5]:
        line = line.strip()
        # 「店」で終わる行を店名と見なす（ただし、長すぎる行や特定キーワードを含む行は除外）
        if line.endswith('店') and len(line) < 30 and not any(kw in line for kw in ["領収書", "登録番号", "電話"]):
            store_name = line
            break  # 最初に見つかったものを採用

    # 「店」が見つからない場合、最初の行をフォールバックとして試す
    if store_name == "不明" and lines:
        first_line = lines[0].strip()
        # 明らかに店名ではないような行（例：日付、長い注意書き）を避ける
        if len(first_line) > 1 and len(first_line) < 30 and not any(kw in first_line for kw in ["領収書", "登録番号", "電話", "年", "月", "日"]):
            store_name = first_line

    # --- 取引日時の抽出 (より厳密な正規表現) ---
    transaction_time = None
    # パターン: 2025年11月12日(水)17:03 または 2025年10月 9日 12:51
    date_pattern = re.compile(
        r'(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日(?:\s*\(.\))?\s*(\d{1,2}):(\d{1,2})')
    for line in lines:
        match = date_pattern.search(line)
        if match:
            try:
                year, month, day, hour, minute = map(int, match.groups())
                transaction_time = datetime(year, month, day, hour, minute)
                break
            except (ValueError, IndexError):
                continue

    # --- 商品リストの抽出 (再々改善版) ---
    items = []
    start_keywords = ['【領収証】', '領収証', '領収書', '内訳']
    end_keywords = ['小計', '合計', '点数', 'お会計']

    # パターン定義
    # Starts with digits and space
    item_line_pattern = re.compile(r'^\d+\s+(.+)')
    quantity_pattern = re.compile(r'\(?(\d+)\s*(?:個|点|x|X)\b')
    price_line_pattern = re.compile(r'^\s*[¥￥][\d,]+')
    # Keywords to filter out lines that are not items
    non_item_keywords = ['年', '月', '日', 'フルセルフ', '電話', 'No.', '登録番号']

    in_items_section = False
    last_item_added = None

    # We need to iterate with an index to look ahead for the price
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        # --- Section Detection ---
        if not in_items_section:
            is_item_like = False
            match = item_line_pattern.search(line)
            if match and not any(kw in line for kw in non_item_keywords):
                has_price_on_same_line = re.search(r'[¥￥]', line)
                is_price_on_next_line = (
                    i + 1 < len(lines)) and price_line_pattern.search(lines[i+1])
                if has_price_on_same_line or is_price_on_next_line:
                    is_item_like = True

            if any(kw in line.replace(' ', '') for kw in start_keywords) or is_item_like:
                in_items_section = True
                if any(kw in line.replace(' ', '') for kw in start_keywords):
                    continue

        if in_items_section and any(keyword in line for keyword in end_keywords):
            break

        # --- Line Parsing within Item Section ---
        if in_items_section:
            # 1. Check for quantity line
            if last_item_added:
                quantity_match = quantity_pattern.search(line)
                if quantity_match:
                    last_item_added['quantity'] = int(quantity_match.group(1))
                    continue

            # 2. Check for item line
            item_match = item_line_pattern.search(line)
            if item_match and not any(kw in line for kw in non_item_keywords):
                has_price_on_same_line = re.search(r'[¥￥]', line)
                is_price_on_next_line = (
                    i + 1 < len(lines)) and price_line_pattern.search(lines[i+1])

                if has_price_on_same_line or is_price_on_next_line:
                    name = item_match.group(1).strip()

                    price_match = re.search(r'\s*[¥￥].*$', name)
                    if price_match:
                        name = name[:price_match.start()].strip()

                    item = {"name": name, "quantity": 1, "price": 0}
                    items.append(item)
                    last_item_added = item
                    continue

    return {
        "store_name": store_name,
        "transaction_time": transaction_time,
        "items": items
    }

# ⭐️ --- 'scan' ビューを修正 --- ⭐️


@login_required
def scan(request):
    if request.method == 'POST':
        image_file = request.FILES.get('receipt_image')
        if not image_file:
            return JsonResponse({'success': False, 'error': '画像ファイルが選択されていません。'})

        image_bytes = image_file.read()
        ocr_text = None
        filename = None  # 保存後のファイル名を保持する変数
        fs = FileSystemStorage()

        # 1. Colab API 処理を試行
        use_colab = getattr(settings, 'USE_COLAB_API', False)
        colab_url = getattr(settings, 'COLAB_API_URL', '')

        if use_colab and colab_url and colab_url != 'YOUR_COLAB_NGROK_URL_HERE':
            try:
                print(f"Calling Colab API at {colab_url} to upload image.")
                files = {'file': (image_file.name, image_bytes,
                                  image_file.content_type)}
                colab_response = requests.post(
                    f"{colab_url}/ocr",
                    files=files,
                    timeout=60
                )
                colab_response.raise_for_status()
                ocr_result = colab_response.json()
                if ocr_result and 'result' in ocr_result:
                    ocr_text = ocr_result['result']
                    print("Successfully received OCR text from Colab API.")
                else:
                    print("Colab API response was invalid.")
            except requests.exceptions.RequestException as e:
                print(
                    f"Colab API request failed: {e}. Falling back to local processing.")
            except Exception as e:
                print(
                    f"An unexpected error occurred with Colab API: {e}. Falling back to local processing.")

        # 2. ローカル処理にフォールバック
        if ocr_text is None:
            print("Falling back to local OCR processing.")
            try:
                # ⭐️ 修正: 'bytes' エラーを回避するため ContentFile でラップ
                content_file = ContentFile(image_bytes)
                filename = fs.save('receipts/' + image_file.name, content_file)
                image_path = fs.path(filename)

                analyzer = DocumentAnalyzer()
                img = cv2.imread(image_path)
                if img is None:
                    raise ValueError("ローカルでの画像ファイルの読み込みに失敗しました。")

                results, _, _ = analyzer(img)  # 同期呼び出し
                ocr_text = "".join(paragraph.contents + "\n" for paragraph in results.paragraphs) if results and hasattr(
                    results, 'paragraphs') else "テキストが検出されませんでした。"
                print("Successfully processed OCR locally.")
            except Exception as e:
                return JsonResponse({'success': False, 'error': f"ローカルOCR処理中にエラーが発生しました: {e}"})

        # 3. OCRテキストをパースして保存
        if ocr_text:
            image_url = None

            # ⭐️ 修正: Colab APIが成功した場合、ここで初めてファイルを保存する
            # (ローカルフォールバック時は 'filename' は既に設定されている)
            if filename is None:
                content_file = ContentFile(image_bytes)
                filename = fs.save('receipts/' + image_file.name, content_file)

            image_url = fs.url(filename)

            # (以下、既存のパース・保存ロジック)
            parsed_data = parse_receipt_data(ocr_text)
            store = None
            if parsed_data['store_name']:
                try:
                    store_name_to_find = parsed_data['store_name'].strip()
                    store = Store.objects.filter(
                        store_name__icontains=store_name_to_find).first()
                except Exception as e:
                    pass

            # 重複チェック
            if store and parsed_data['transaction_time']:
                existing_receipt = Receipt.objects.filter(
                    user=request.user,
                    store=store,
                    transaction_time=parsed_data['transaction_time']
                ).first()

                if existing_receipt:
                    return JsonResponse({'success': False, 'error': 'このレシートは既に登録済みです。'})

            receipt = Receipt.objects.create(
                user=request.user,
                image_url=image_url,
                ocr_text=ocr_text,
                store=store,
                transaction_time=parsed_data['transaction_time'],
                parsed_data=parsed_data['items']
            )
            redirect_url = reverse('core:receipt_detail', kwargs={
                                   'receipt_id': receipt.id})
            return JsonResponse({'success': True, 'redirect_url': redirect_url})
        else:
            return JsonResponse({'success': False, 'error': 'APIとローカル処理の両方でOCRテキストの取得に失敗しました。'})

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
        form = AnnouncementForm(
            request.POST, request.FILES, instance=announcement)
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
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL,
                      [inquiry.reply_to_email])
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
