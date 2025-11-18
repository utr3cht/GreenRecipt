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
import uuid  # Add this
import os   # Add this

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
    OCRテキストから店舗名、取引日時、商品リスト、合計点数を抽出する。
    価格行の前の行を商品名と見なすロジックを主軸とする。
    """
    lines = text.split('\n')
    
    # --- 店舗名、取引日時の抽出（既存のロジックを流用・簡略化） ---
    store_name = lines[0] if lines else "不明"
    transaction_time = None
    date_pattern = re.compile(r'(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日.*?(\d{1,2}):(\d{2})')
    for line in lines:
        match = date_pattern.search(line)
        if match:
            try:
                year, month, day, hour, minute = map(int, match.groups())
                transaction_time = datetime(year, month, day, hour, minute)
                break
            except (ValueError, IndexError):
                continue

    # --- 合計点数の直接抽出 ---
    total_quantity_from_receipt = 0
    quantity_total_pattern = re.compile(r'(?:買上点数|点数)\s*(\d+) *点?')
    for line in lines:
        match = quantity_total_pattern.search(line)
        if match:
            total_quantity_from_receipt = int(match.group(1))
            break

    # --- 商品リストの抽出 ---
    items = []
    end_keywords = ['小計', '合計', '外税', 'お預り', 'お釣り']
    price_pattern = re.compile(r'¥([\d,]+)※?$')
    quantity_pattern = re.compile(r'\(?\s*(\d+)\s*(?:個|点|x|X)\b')

    for i, line in enumerate(lines):
        line = line.strip()
        
        # 終了キーワードが見つかったらループを抜ける
        if any(kw in line for kw in end_keywords):
            break
            
        # 価格行のパターンにマッチするか確認
        price_match = price_pattern.search(line)
        if price_match and i > 0:
            # 価格がマッチした場合、その前の行を商品名と見なす
            item_name = lines[i-1].strip()
            
            # 商品名が空、または明らかに商品名でないものを除外
            if not item_name or item_name.startswith('¥') or len(item_name) > 50:
                continue

            try:
                price = int(price_match.group(1).replace(',', ''))
                item = {"name": item_name, "quantity": 1, "price": price}
                items.append(item)
            except (ValueError, IndexError):
                continue

        # 数量行のパターンにマッチするか確認
        quantity_match = quantity_pattern.search(line)
        if quantity_match and items:
            # 直前の商品の数量を更新
            items[-1]['quantity'] = int(quantity_match.group(1))

    # 抽出した合計点数があれば、それを優先する
    final_total_quantity = total_quantity_from_receipt if total_quantity_from_receipt > 0 else sum(item.get('quantity', 0) for item in items)

    return {
        "store_name": store_name,
        "transaction_time": transaction_time,
        "items": items,
        "total_quantity": final_total_quantity
    }


@login_required
def scan(request):
    if request.method == 'POST':
        image_file = request.FILES.get('receipt_image')
        if not image_file:
            return JsonResponse({'success': False, 'error': '画像ファイルが選択されていません。'})

        image_bytes = image_file.read()
        ocr_text = None
        fs = FileSystemStorage()

        # --- 新しい安全なファイル名を生成 ---
        original_filename = image_file.name
        ext = os.path.splitext(original_filename)[1]
        safe_filename = f"{uuid.uuid4().hex}{ext}"

        # 1. Colab API 処理を試行
        use_colab = getattr(settings, 'USE_COLAB_API', False)
        colab_url = getattr(settings, 'COLAB_API_URL', '')

        if use_colab and colab_url and colab_url != 'YOUR_COLAB_NGROK_URL_HERE':
            try:
                print(f"Calling Colab API at {colab_url} to upload image.")
                # Colab APIには元のファイル名を渡す (API側で処理されるため)
                files = {'file': (original_filename, image_bytes,
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
                # 画像データをメモリからデコードしてOCR処理
                nparr = np.frombuffer(image_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is None:
                    raise ValueError(
                        "画像ファイルのデコードに失敗しました。ファイルが破損しているか、サポートされていない形式の可能性があります。")

                # --- DEBUGGING: Save decoded image ---
                debug_image_path = os.path.join(
                    settings.MEDIA_ROOT, 'debug_images', f'decoded_{safe_filename}')
                os.makedirs(os.path.dirname(debug_image_path), exist_ok=True)
                cv2.imwrite(debug_image_path, img)
                print(f"[DEBUG] デコードされた画像を保存しました: {debug_image_path}")
                print(f"[DEBUG] デコードされた画像の形状: {img.shape}")
                # --- END DEBUGGING ---

                analyzer = DocumentAnalyzer()
                results, _, _ = analyzer(img)  # 同期呼び出し
                ocr_text = "".join(paragraph.contents + "\n" for paragraph in results.paragraphs) if results and hasattr(
                    results, 'paragraphs') else "テキストが検出されませんでした。"
                print("Successfully processed OCR locally from memory.")
            except Exception as e:
                return JsonResponse({'success': False, 'error': f"ローカルOCR処理中にエラーが発生しました: {e}"})

        # 3. OCRテキストをパースして保存
        if ocr_text:
            # ファイルを保存 (安全なファイル名を使用)
            content_file = ContentFile(image_bytes)
            filename = fs.save('receipts/' + safe_filename,
                               content_file)  # Use safe_filename here

            image_url = fs.url(filename)

            # (以下、既存のパース・保存ロジック)
            parsed_data = parse_receipt_data(ocr_text)
            store = None
            if parsed_data['store_name']:
                try:
                    store_name_to_find = parsed_data['store_name'].strip()
                    store = Store.objects.filter(
                        store_name__icontains=store_name_to_find).first()
                except Exception:
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
                parsed_data=parsed_data
            )
            redirect_url = reverse('core:receipt_detail', kwargs={
                                   'receipt_id': receipt.id})
            return JsonResponse({'success': True, 'redirect_url': redirect_url})

    return render(request, "core/scan.html")


@login_required
def ai_report(request):
    user_receipts = Receipt.objects.filter(user=request.user)
    total_items_purchased = sum(receipt.total_quantity for receipt in user_receipts)
    total_ec_points = sum(receipt.ec_points for receipt in user_receipts)
    context = {
        'total_items_purchased': total_items_purchased,
        'total_ec_points': total_ec_points,
    }
    return render(request, "core/ai_report.html", context)

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
            # If delete checkbox is checked, delete the old file.
            if form.cleaned_data.get('delete_file'):
                if announcement.file:
                    # Delete from storage, don't save the model yet.
                    announcement.file.delete(save=False)

            # form.save() will handle saving the new file if uploaded,
            # or clearing the file field if 'delete_file' was checked and no new file was uploaded.
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
