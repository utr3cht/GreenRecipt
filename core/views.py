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
        'rank': user.rank,
        'current_points': user.current_points,
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
    Extract store name, transaction time, and item list from OCR text.
    Handles complex cases where item code, name, and price are on separate lines.
    """
    translation_map = str.maketrans(
        '　Ｏ０oOоО１１iIíÍl丨２２３３４４５５６６７７８８９９￥円',
        '  00000011111112233445566778899¥¥'
    )
    text = text.translate(translation_map)
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    # Extract store name
    store_name = "Unknown"
    store_keywords = ['店', 'ストア', 'スーパー', 'マート', 'ドラッグ', '薬局', 'TOP', 'MARKET']
    exclude_keywords = ['領収書', '登録番号', 'TEL', '電話', '#', '年', '月', '日', '精算']

    for line in lines[:10]:
        if any(kw in line for kw in exclude_keywords):
            continue
        if any(kw in line for kw in store_keywords) and 3 <= len(line) <= 50:
            store_name = line
            break

    # Extract transaction time
    transaction_time = None
    datetime_pattern = re.compile(
        r'(\d{4})\s*年?\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日.*?(\d{1,2})\s*:\s*(\d{2})'
    )

    for line in lines:
        match = datetime_pattern.search(line)
        if match:
            try:
                year, month, day, hour, minute = map(int, match.groups())
                if 2020 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
                    transaction_time = datetime(year, month, day, hour, minute)
                    break
            except (ValueError, IndexError):
                continue

    # Extract items
    items = []
    end_keywords = ['小計', '合計', '点数', '外税', '買上点数', 'お預り', 'お釣り', '税率']

    item_code_pattern = re.compile(r'^\s*(\d{4})\s+(.+)$')
    price_pattern = re.compile(r'¥\s*([\d,]+)')
    quantity_pattern = re.compile(r'^\s*[(\s]*(\d+)\s*個?\s*[×xX]\s*@(\d+)')
    item_code_only_pattern = re.compile(r'^\s*\d{4}\s*$')

    i = 0
    pending_price = None

    while i < len(lines):
        line = lines[i]

        if any(kw in line for kw in end_keywords):
            break

        # Pattern 1: Item code + name on same line
        code_match = item_code_pattern.match(line)
        if code_match:
            code = code_match.group(1)
            name_part = code_match.group(2).strip()

            price_in_name = price_pattern.search(name_part)
            if price_in_name:
                name = name_part[:price_in_name.start()
                                 ].strip().replace('※', '')
                try:
                    price = int(price_in_name.group(1).replace(',', ''))
                except ValueError:
                    price = None
            else:
                name = name_part.replace('※', '')
                price = None

            quantity = 1
            j = i + 1
            found_quantity = False

            while j < len(lines) and price is None:
                next_line = lines[j]

                if any(kw in next_line for kw in end_keywords):
                    break

                if item_code_pattern.match(next_line) or item_code_only_pattern.match(next_line):
                    break

                price_match = price_pattern.search(next_line)
                if price_match:
                    try:
                        price = int(price_match.group(1).replace(',', ''))
                        j += 1
                        break
                    except ValueError:
                        pass

                j += 1

            while j < len(lines) and not found_quantity:
                check_line = lines[j]

                if any(kw in check_line for kw in end_keywords):
                    break
                if item_code_pattern.match(check_line) or item_code_only_pattern.match(check_line):
                    break

                qty_match = quantity_pattern.match(check_line)
                if qty_match:
                    quantity = int(qty_match.group(1))
                    found_quantity = True
                    j += 1
                    break

                j += 1

            if price is None and pending_price:
                price = pending_price
                pending_price = None

            if name and price and 10 <= price <= 100000:
                items.append({
                    "name": name,
                    "quantity": quantity,
                    "price": price
                })

            i = j
            continue

        # Pattern 2: Item code only (name on next line)
        if item_code_only_pattern.match(line):
            code = line.strip()

            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()

                if not price_pattern.match(next_line):
                    name = next_line.replace('※', '')

                    price = None
                    quantity = 1
                    found_quantity = False
                    j = i + 2

                    while j < len(lines):
                        check_line = lines[j]

                        if any(kw in check_line for kw in end_keywords):
                            break
                        if item_code_pattern.match(check_line) or item_code_only_pattern.match(check_line):
                            break

                        price_match = price_pattern.search(check_line)
                        if price_match:
                            try:
                                price = int(price_match.group(
                                    1).replace(',', ''))
                                j += 1
                                break
                            except ValueError:
                                pass

                        j += 1

                    while j < len(lines) and not found_quantity:
                        check_line = lines[j]

                        if any(kw in check_line for kw in end_keywords):
                            break
                        if item_code_pattern.match(check_line) or item_code_only_pattern.match(check_line):
                            break

                        qty_match = quantity_pattern.match(check_line)
                        if qty_match:
                            quantity = int(qty_match.group(1))
                            found_quantity = True
                            j += 1
                            break

                        j += 1

                    if price is None and pending_price:
                        price = pending_price
                        pending_price = None

                    if name and price and 10 <= price <= 100000:
                        items.append({
                            "name": name,
                            "quantity": quantity,
                            "price": price
                        })

                    i = j
                    continue

        # Pattern 3: Price only line (before item name)
        price_match = price_pattern.match(line)
        if price_match:
            try:
                pending_price = int(price_match.group(1).replace(',', ''))
            except ValueError:
                pass

        i += 1

    # Clean item names
    for item in items:
        item['name'] = re.sub(r'^\d{4}\s+', '', item['name'])
        item['name'] = re.sub(r'\s+\d+$', '', item['name'])
        item['name'] = re.sub(r'\s*¥.*$', '', item['name'])
        item['name'] = ' '.join(item['name'].split())
        item['name'] = item['name'].strip()

    return {
        "store_name": store_name,
        "transaction_time": transaction_time,
        "items": items
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
                parsed_data=parsed_data['items']
            )
            redirect_url = reverse('core:receipt_detail', kwargs={
                                   'receipt_id': receipt.id})
            return JsonResponse({'success': True, 'redirect_url': redirect_url})

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
