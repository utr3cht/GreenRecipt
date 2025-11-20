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
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.utils.decorators import method_decorator
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
import numpy as np  # Add this line

from django.db import transaction

# Forms
from .forms import InquiryForm, ReplyForm, StoreForm, AnnouncementForm, CouponForm, GrantCouponForm, EcoProductForm
# ⭐️ 修正: StoreUserCreationForm は accounts.forms からインポート
from accounts.forms import StoreUserCreationForm

# Models
from .models import Inquiry, Store, Announcement, Receipt, Coupon, Product, ReceiptItem, EcoProduct
from accounts.models import CustomUser

# --- 認証関連ビュー ---


def admin_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_superuser or user.role in ['admin', 'store']:
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
        if request.user.is_superuser or request.user.role in ['admin', 'store']:
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
    OCRテキストから店舗名、取引日時、商品リスト、合計などを抽出する。（改善版）
    - 様々な日付フォーマットに対応。
    - 複数行にわたる商品情報や、1行にまとまった商品情報に対応。
    - 合計金額、合計点数の抽出精度を向上。
    """
    lines = text.split('\n')
    lines = [line.strip() for line in lines if line.strip()]

    store_name = "不明"
    title_line = ""
    branch_line = ""

    if lines:
        title_line = lines[0]

    for line in lines[1:5]:
        if line.endswith('店'):
            branch_line = line
            break
    
    if title_line and branch_line and "HP" not in title_line:
        store_name = f"{title_line} {branch_line}"
    elif branch_line:
        store_name = branch_line
    elif title_line:
        store_name = title_line
    else:
        store_name = "不明"

    transaction_time = None
    date_line_index = -1
    date_pattern = re.compile(
        r'(\d{2,4})[年/](\d{1,2})[月/](\d{1,2})日?\(?\w?\)?\s*(\d{1,2}):(\d{2})'
    )
    for i, line in enumerate(lines):
        match = date_pattern.search(line)
        if match:
            try:
                year_str, month_str, day_str, hour_str, minute_str = match.groups()
                year, month, day, hour, minute = map(
                    int, [year_str, month_str, day_str, hour_str, minute_str])
                if year < 100:
                    year += 2000
                transaction_time = datetime(year, month, day, hour, minute)
                date_line_index = i
                break
            except (ValueError, IndexError):
                continue

    total_quantity_from_receipt = 0
    total_amount_from_receipt = 0
    quantity_total_pattern = re.compile(r'(?:合計点数|買上点数|点数)\s*(\d+)')
    amount_total_pattern = re.compile(r'(?:(?:御)?合計|小計)\s*¥?([\d,]+)')

    for line in lines:
        qty_match = quantity_total_pattern.search(line)
        if qty_match:
            total_quantity_from_receipt = int(qty_match.group(1))
        amt_match = amount_total_pattern.search(line)
        if amt_match:
            total_amount_from_receipt = int(amt_match.group(1).replace(',', ''))

    items = []
    start_index = date_line_index + 1 if date_line_index != -1 else 0
    end_index = len(lines)

    for i, line in enumerate(lines[start_index:]):
        if any(keyword in line for keyword in ['小計', '合計', 'クレジット', 'お預り']):
            end_index = start_index + i
            break

    item_lines = lines[start_index:end_index]

    # 商品行の正規表現
    single_line_pattern = re.compile(r'^\d{4}\s+(.+?)\s+¥([\d,]+)※?$')
    name_pattern = re.compile(r'^\d{4}\s+(.+)$')
    price_pattern = re.compile(r'^¥([\d,]+)※?$')
    quantity_pattern = re.compile(r'\(?\s*(\d+)\s*[個xX]')

    i = 0
    while i < len(item_lines):
        line = item_lines[i]
        
        # 1行パターン
        single_match = single_line_pattern.search(line)
        if single_match:
            name = single_match.group(1).strip()
            price = int(single_match.group(2).replace(',', ''))
            items.append({"name": name, "quantity": 1, "price": price})
            i += 1
        # 2行パターン
        else:
            name_match = name_pattern.search(line)
            if name_match and i + 1 < len(item_lines):
                next_line = item_lines[i+1]
                price_match = price_pattern.search(next_line)
                if price_match:
                    name = name_match.group(1).strip()
                    price = int(price_match.group(1).replace(',', ''))
                    items.append({"name": name, "quantity": 1, "price": price})
                    i += 2
                else:
                    i += 1 # nameはあったがpriceがなかった
            else:
                i += 1 # 何にもマッチせず
            
        # 数量行のチェック (itemsに追加された後)
        if items and i < len(item_lines):
            qty_line = item_lines[i]
            qty_match = quantity_pattern.search(qty_line)
            if qty_match:
                quantity = int(qty_match.group(1))
                items[-1]['quantity'] = quantity
                i += 1 # 数量行を消費

    final_total_quantity = total_quantity_from_receipt if total_quantity_from_receipt > 0 else sum(
        item.get('quantity', 1) for item in items)

    return {
        "store_name": store_name,
        "transaction_time": transaction_time,
        "items": items,
        "total_quantity": final_total_quantity,
        "total_amount": total_amount_from_receipt
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

                print("[INFO] Initializing DocumentAnalyzer...")
                analyzer = DocumentAnalyzer()
                print("[INFO] DocumentAnalyzer initialized. Starting analysis...")
                results, _, _ = analyzer(img)  # 同期呼び出し
                print("[INFO] Analysis complete. Processing results...")

                if results and hasattr(results, 'paragraphs') and results.paragraphs:
                    ocr_text = "".join(paragraph.contents +
                                       "\n" for paragraph in results.paragraphs)
                    print("[INFO] Successfully extracted text from OCR results.")
                else:
                    ocr_text = "テキストが検出されませんでした。"
                    print(
                        "[WARN] No text detected or paragraphs attribute is missing/empty in the result.")
                    if results:
                        print(
                            f"[DEBUG] Raw result object type: {type(results)}")
                        # Note: Printing the full result might be too verbose.
                        # Check attributes available in the result object.
                        print(f"[DEBUG] Result attributes: {dir(results)}")

                print("Successfully processed OCR locally from memory.")
            except Exception as e:
                # エラーログをより詳細に出力
                import traceback
                print(
                    f"[ERROR] An exception occurred during local OCR processing: {e}")
                print(f"[ERROR] Traceback: {traceback.format_exc()}")
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
            if parsed_data['store_name'] and parsed_data['store_name'] != "不明":
                store_name_to_find = parsed_data['store_name'].strip()
                # get_or_create を使用して、店舗が存在しない場合は作成する
                store, created = Store.objects.get_or_create(
                    store_name=store_name_to_find,
                    defaults={'category': 'other', 'address': '不明'} # 新規作成時のデフォルト値
                )
            # 重複チェック
            if store and parsed_data['transaction_time']:
                existing_receipt = Receipt.objects.filter(
                    user=request.user,
                    store=store,
                    transaction_time=parsed_data['transaction_time']
                ).first()

                if existing_receipt:
                    return JsonResponse({'success': False, 'error': 'このレシートは既に登録済みです。'})

            try:
                with transaction.atomic():
                    # parsed_dataからdatetimeオブジェクトを削除または文字列に変換
                    data_to_save = parsed_data.copy()
                    if 'transaction_time' in data_to_save:
                        del data_to_save['transaction_time']

                    # まずレシート本体を作成
                    receipt = Receipt.objects.create(
                        user=request.user,
                        image_url=image_url,
                        ocr_text=ocr_text,
                        store=store,
                        transaction_time=parsed_data['transaction_time'],
                        parsed_data=data_to_save  # datetimeを除いた辞書を保存
                    )

                    # エコ商品のリストを事前に取得
                    eco_products = list(EcoProduct.objects.all())
                    total_eco_points_to_add = 0
                    # 同じ商品での重複加算を防ぐ
                    processed_products = set()

                    # パースされたアイテムをReceiptItemモデルに保存
                    if parsed_data['items']:
                        for item_data in parsed_data['items']:
                            # 商品名が空の場合はスキップ
                            if not item_data.get('name'):
                                continue

                            product, created = Product.objects.get_or_create(
                                name=item_data['name']
                            )
                            ReceiptItem.objects.create(
                                receipt=receipt,
                                product=product,
                                # quantityがない場合のデフォルト値
                                quantity=item_data.get('quantity', 1),
                                # priceがない場合のデフォルト値
                                price=item_data.get('price', 0)
                            )

                            # ポイント加算ロジック
                            # まだこの商品でポイント加算していなければ処理
                            if product.id not in processed_products:
                                for eco_product in eco_products:
                                    # 商品名にエコ商品のキーワードが含まれているかチェック
                                    if eco_product.name in product.name:
                                        total_eco_points_to_add += eco_product.points
                                        processed_products.add(product.id)
                                        # 1つの商品が複数のエコ商品にマッチしても、最初の1つで抜ける
                                        break

                    # 合計ポイントを加算してユーザー情報を更新
                    if total_eco_points_to_add > 0:
                        user = request.user
                        user.current_points += total_eco_points_to_add
                        user.save()

            except Exception as e:
                # トランザクション内でエラーが起きた場合
                import traceback
                print(
                    f"[ERROR] An exception occurred during receipt saving transaction: {e}")
                print(f"[ERROR] Traceback: {traceback.format_exc()}")
                return JsonResponse({'success': False, 'error': f"レシートの保存中にエラーが発生しました: {e}"})

            redirect_url = reverse('core:receipt_detail', kwargs={
                                   'receipt_id': receipt.id})
            return JsonResponse({'success': True, 'redirect_url': redirect_url})

    return render(request, "core/scan.html")


@login_required
def ai_report(request):
    user_receipts = Receipt.objects.filter(user=request.user)
    total_items_purchased = sum(
        receipt.total_quantity for receipt in user_receipts)
    
    # Eco-friendly product calculation
    eco_product_names = list(EcoProduct.objects.values_list('name', flat=True))
    total_eco_items = 0
    if eco_product_names:
        # Get all receipt items for the user
        user_receipt_items = ReceiptItem.objects.filter(receipt__user=request.user)
        for item in user_receipt_items:
            # Check if any eco-product keyword is in the item name
            if any(eco_name in item.product.name for eco_name in eco_product_names):
                total_eco_items += item.quantity

    total_ec_points = sum(receipt.ec_points for receipt in user_receipts)

    context = {
        'total_items_purchased': total_items_purchased,
        'total_ec_points': total_ec_points,
        'total_eco_items': total_eco_items,
    }
    # return render(request, "core/ai_report.html", context)
    return render(request, "core/notai_report.html", context)

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
def coupon_create(request):
    if request.method == 'POST':
        form = CouponForm(request.POST)
        if form.is_valid():
            form.save()
            # Redirect to a new coupon list page (which I will create next)
            return redirect('core:coupon_list_admin')
    else:
        form = CouponForm()
    return render(request, 'admin/coupon_create.html', {'form': form})


@staff_member_required
def coupon_list_admin(request):
    coupons = Coupon.objects.all()
    return render(request, 'admin/coupon_list_admin.html', {'coupons': coupons})


@staff_member_required
def coupon_update(request, coupon_id):
    coupon = get_object_or_404(Coupon, pk=coupon_id)
    if request.method == 'POST':
        form = CouponForm(request.POST, instance=coupon)
        if form.is_valid():
            form.save()
            return redirect('core:coupon_list_admin')
    else:
        form = CouponForm(instance=coupon)
    return render(request, 'admin/coupon_update.html', {'form': form, 'coupon': coupon})


@staff_member_required
def coupon_delete(request, coupon_id):
    coupon = get_object_or_404(Coupon, pk=coupon_id)
    coupon.delete()
    # Optionally, add a success message
    # messages.success(request, f'クーポン「{coupon.title}」を削除しました。')
    return redirect('core:coupon_list_admin')


@staff_member_required
def grant_coupon_admin(request):
    if request.method == 'POST':
        form = GrantCouponForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            coupon = form.cleaned_data['coupon']
            user.current_coupons.add(coupon)
            messages.success(
                request, f'ユーザー「{user.username}」にクーポン「{coupon.title}」を付与しました。')
            return redirect('core:grant_coupon_admin')
    else:
        form = GrantCouponForm()
    return render(request, 'admin/grant_coupon_admin.html', {'form': form})


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


# EcoProduct管理ビュー
@method_decorator(staff_member_required, name='dispatch')
class EcoProductListView(ListView):
    model = EcoProduct
    template_name = 'admin/ecoproduct_list.html'
    context_object_name = 'ecoproducts'


@method_decorator(staff_member_required, name='dispatch')
class EcoProductCreateView(CreateView):
    model = EcoProduct
    form_class = EcoProductForm
    template_name = 'admin/ecoproduct_form.html'
    success_url = reverse_lazy('core:ecoproduct_list')


@method_decorator(staff_member_required, name='dispatch')
class EcoProductUpdateView(UpdateView):
    model = EcoProduct
    form_class = EcoProductForm
    template_name = 'admin/ecoproduct_form.html'
    success_url = reverse_lazy('core:ecoproduct_list')


@method_decorator(staff_member_required, name='dispatch')
class EcoProductDeleteView(DeleteView):
    model = EcoProduct
    template_name = 'admin/ecoproduct_confirm_delete.html'
    success_url = reverse_lazy('core:ecoproduct_list')
