# Django Imports
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.admin.views.decorators import staff_member_required
from django.core import serializers
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import (
    CouponForm, StoreForm, EcoProductForm, AnnouncementForm, 
    InquiryForm, StoreEcoProductForm, StoreCouponForm
)
from yomitoku.document_analyzer import DocumentAnalyzer
import cv2
import re
from datetime import datetime
from django.utils import timezone
import json
from django.core.serializers.json import DjangoJSONEncoder
import requests  # Add this import
from django.core.files.base import ContentFile  # fs.saveエラーを修正するために追加
import uuid  # Add this
import os   # Add this
import numpy as np  # Add this line
import google.generativeai as genai
import calendar

from django.db import transaction, models

# Forms
from .forms import InquiryForm, ReplyForm, StoreForm, AnnouncementForm, CouponForm, GrantCouponForm, EcoProductForm
from accounts.forms import StoreUserCreationForm

# Models
from .models import Inquiry, InquiryMessage, Store, Announcement, Receipt, Coupon, Product, ReceiptItem, EcoProduct, CouponUsage, Report
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


@login_required
def staff_logout(request):
    logout(request)
    return redirect("core:staff_login")


# --- 店舗用ビュー ---

@login_required
def store_dashboard(request):
    if request.user.role != 'store':
        return redirect('core:staff_index')
    
    # 自店舗の申請状況
    if not request.user.store:
        return render(request, 'core/store/error.html', {'message': '店舗情報が紐付いていません。'})
        
    store = request.user.store
    my_products = EcoProduct.objects.filter(store=store).exclude(status='rejected').order_by('-pk')
    my_coupons = Coupon.objects.filter(store=store).exclude(status='rejected').order_by('-pk')
    
    context = {
        'products': my_products,
        'coupons': my_coupons,
    }
    return render(request, 'core/store/dashboard.html', context)

class StoreEcoProductCreateView(LoginRequiredMixin, CreateView):
    model = EcoProduct
    form_class = StoreEcoProductForm
    template_name = 'core/store/product_form.html'
    success_url = reverse_lazy('core:store_dashboard')

    def form_valid(self, form):
        if self.request.user.role != 'store' or not self.request.user.store:
            return redirect('core:staff_index') # あるいはエラー表示
            
        form.instance.store = self.request.user.store
        form.instance.status = 'pending'
        return super().form_valid(form)

class StoreCouponCreateView(LoginRequiredMixin, CreateView):
    model = Coupon
    form_class = StoreCouponForm
    template_name = 'core/store/coupon_form.html'
    success_url = reverse_lazy('core:store_dashboard')

    def form_valid(self, form):
        if self.request.user.role != 'store' or not self.request.user.store:
            return redirect('core:staff_index')
            
        form.instance.store = self.request.user.store
        form.instance.status = 'pending'
        # available_stores に自店舗を追加する必要がある（保存後）
        response = super().form_valid(form)
        self.object.available_stores.add(self.request.user.store)
        return response


# --- 承認管理ビュー ---

@login_required
@user_passes_test(lambda u: u.is_staff or u.role == 'admin')
def approval_list(request):
    pending_products = EcoProduct.objects.filter(status='pending')
    pending_coupons = Coupon.objects.filter(status='pending')
    
    context = {
        'products': pending_products,
        'coupons': pending_coupons
    }
    return render(request, 'core/admin/approval_list.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff or u.role == 'admin')
def approve_item(request, type, id):
    if request.method == 'POST':
        if type == 'product':
            item = get_object_or_404(EcoProduct, pk=id)
        elif type == 'coupon':
            item = get_object_or_404(Coupon, pk=id)
        else:
            return redirect('core:approval_list')
        
        item.status = 'approved'
        item.save()
        messages.success(request, f'{item} を承認しました。')
    return redirect('core:approval_list')

@staff_member_required
@require_POST
def reject_item(request, type, id):
    if type == 'product':
        item = get_object_or_404(EcoProduct, id=id)
    elif type == 'coupon':
        item = get_object_or_404(Coupon, id=id)
    else:
        return redirect('core:approval_list')
    
    # 削除申請の却下の場合（承認に戻す）
    if item.status == 'deletion_requested':
        item.status = 'approved'
        item.save()
        messages.info(request, f"{'商品' if type == 'product' else 'クーポン'}「{item.name if type == 'product' else item.title}」の削除申請を却下しました（ステータスを承認済みに戻しました）。")
    else:
        # 通常の承認申請の却下
        item.status = 'rejected'
        reason = request.POST.get('rejection_reason', '').strip()
        print(f"Rejecting item {item} with reason: '{reason}'")  # Debug Logging
        if reason:
            item.rejection_reason = reason
        item.save()
        messages.warning(request, f"{'商品' if type == 'product' else 'クーポン'}「{item.name if type == 'product' else item.title}」を却下しました。")
    
    return redirect('core:approval_list')

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
    MAX_POINTS = 800
    # ランク進捗の計算
    current_points = user.current_points
    next_rank_points = 0
    prev_rank_points = 0
    
    if current_points < 100:
        next_rank_points = 100
        prev_rank_points = 0
    elif current_points < 300:
        next_rank_points = 300
        prev_rank_points = 100
    elif current_points < 800:
        next_rank_points = 800
        prev_rank_points = 300
    else:
        next_rank_points = None # Max rank
        prev_rank_points = 800

    progress_percentage = 100
    points_to_next = 0

    if next_rank_points:
        points_to_next = next_rank_points - current_points
        range_points = next_rank_points - prev_rank_points
        if range_points > 0:
            progress_points = current_points - prev_rank_points
            progress_percentage = int((progress_points / range_points) * 100)
        else:
            progress_percentage = 0

    context = {
        'announcements': announcements,
        'coupons': coupons,
        'receipts': receipts,
        'rank': user.rank,
        'current_points': user.current_points,
        'next_rank_points': next_rank_points,
        'points_to_next': points_to_next,
        'progress_percentage': progress_percentage,
    }
    return render(request, "core/main_menu.html", context)


@login_required
def coupon_list(request):
    # 所持クーポン
    owned_coupons = request.user.current_coupons.all()
    # 使用済みクーポンID
    used_coupon_ids = CouponUsage.objects.filter(user=request.user).values_list('coupon_id', flat=True)
    
    # 排他制御: 既に所持または使用済みのクーポンと同じ `required_points` を持つクーポンは取得リストに出さない。
    # 1. ユーザーが関与した（所持 or 使用済み）クーポンのIDリスト
    involved_coupon_ids = list(owned_coupons.values_list('id', flat=True)) + list(used_coupon_ids)
    
    # 2. それらのクーポンの `required_points` を取得
    #    (未設定(0)などは除外するか要検討だが、一旦すべて対象とする)
    acquired_point_thresholds = Coupon.objects.filter(
        id__in=involved_coupon_ids
    ).values_list('required_points', flat=True).distinct()
    
    # 3. 取得可能なクーポン
    #    - ステータスが承認済み ('approved')
    #    - まだ関与していない (exclude involved_coupon_ids)
    #    - かつ、既に関与したポイント帯ではない (exclude required_points__in=acquired_point_thresholds)
    available_coupons = Coupon.objects.filter(status='approved').exclude(
        id__in=involved_coupon_ids
    ).exclude(
        required_points__in=acquired_point_thresholds
    ).order_by('required_points')

    # 使用済みクーポンオブジェクトの取得
    used_coupons = Coupon.objects.filter(id__in=used_coupon_ids)

    context = {
        'coupons': owned_coupons,
        'available_coupons': available_coupons,
        'used_coupons': used_coupons,
        'user_points': request.user.current_points
    }
    return render(request, "core/coupon_list.html", context)


@login_required
@require_POST
def acquire_coupon(request, coupon_id):
    try:
        coupon = Coupon.objects.get(pk=coupon_id)
        user = request.user
        
        # 承認済みか確認
        if coupon.status != 'approved':
            return JsonResponse({'success': False, 'error': 'このクーポンはまだ承認されていません。'}, status=400)
        
        # 既に持っていないか確認
        if user.current_coupons.filter(pk=coupon_id).exists():
            return JsonResponse({'success': False, 'error': '既にこのクーポンを持っています。'}, status=400)
            
        # 過去に使用していないか確認
        if CouponUsage.objects.filter(user=user, coupon=coupon).exists():
             return JsonResponse({'success': False, 'error': 'このクーポンは既に使用済みです。'}, status=400)

        # 排他制御: 同じ required_points のクーポンを既に持っているか、使用済みならNG
        # 現在所持している他のクーポンで、同じポイントのものがあるか
        if user.current_coupons.filter(required_points=coupon.required_points).exists():
            return JsonResponse({'success': False, 'error': 'このポイント帯のクーポンは既に取得済みです。'}, status=400)

        # 過去に使用したクーポンで、同じポイントのものがあるか
        # CouponUsage -> coupon -> required_points
        if CouponUsage.objects.filter(user=user, coupon__required_points=coupon.required_points).exists():
            return JsonResponse({'success': False, 'error': 'このポイント帯のクーポンは既に利用済みです。'}, status=400)

        # ポイント確認 (消費はしないが条件として確認)
        if user.current_points < coupon.required_points:
            return JsonResponse({'success': False, 'error': f'ポイントが不足しています。必要ポイント: {coupon.required_points}pt'}, status=400)
        
        with transaction.atomic():
            # ポイント消費はしない
            
            # クーポン付与
            user.current_coupons.add(coupon)
            
        return JsonResponse({'success': True, 'new_points': user.current_points})
        
    except Coupon.DoesNotExist:
        return JsonResponse({'success': False, 'error': '指定されたクーポンが見つかりません。'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'エラーが発生しました: {str(e)}'}, status=500)


@login_required
@require_POST
def use_coupon(request, coupon_id):
    try:
        coupon_to_use = request.user.current_coupons.get(pk=coupon_id)
        
        # 店舗IDを取得（JSONリクエストを想定）
        # リクエストボディのサイズ制限 (10KB)
        if len(request.body) > 10 * 1024:
             return JsonResponse({'success': False, 'error': 'リクエストサイズが大きすぎます。'}, status=400)

        import json
        store_id = None
        if request.body:
            try:
                data = json.loads(request.body)
                store_id = data.get('store_id')
            except json.JSONDecodeError:
                pass
        
        store = None
        if store_id:
            try:
                store = Store.objects.get(pk=store_id)
            except Store.DoesNotExist:
                pass

        # 利用履歴を作成
        CouponUsage.objects.create(
            user=request.user,
            coupon=coupon_to_use,
            store=store
        )

        request.user.current_coupons.remove(coupon_to_use)
        return JsonResponse({'success': True})
    except Coupon.DoesNotExist:
        return JsonResponse({'success': False, 'error': '指定されたクーポンが見つかりません。'}, status=404)


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
        r'(\d{4})[年/]\s*(\d{1,2})[月/]\s*(\d{1,2})日.*\s*(\d{1,2}):(\d{2})'
    )
    for i, line in enumerate(lines):
        print(f"[DEBUG] Date parsing - Processing line: '{line}'") # デバッグ追加
        match = date_pattern.search(line)
        if match:
            print(f"[DEBUG] Date parsing - Match found for line: '{line}'") # デバッグ追加
            print(f"[DEBUG] Date parsing - Matched groups: {match.groups()}") # デバッグ追加
            try:
                year_str, month_str, day_str, hour_str, minute_str = match.groups()
                year, month, day, hour, minute = map(
                    int, [year_str, month_str, day_str, hour_str, minute_str])
                if year < 100:
                    year += 2000
                transaction_time = datetime(year, month, day, hour, minute)
                date_line_index = i
                print(f"[DEBUG] Date parsing - Successfully extracted: {transaction_time}") # デバッグ追加
                break
            except (ValueError, IndexError) as e: # エラー出力も追加
                print(f"[DEBUG] Date parsing - Error converting date parts: {e} for groups: {match.groups()}") # デバッグ追加
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

        # ファイルサイズ制限 (5MB)
        if image_file.size > 5 * 1024 * 1024:
            return JsonResponse({'success': False, 'error': 'ファイルサイズは5MB以下にしてください。'})

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
            # URLにスキームが含まれていない場合、HTTPSを追加
            if not colab_url.startswith('http://') and not colab_url.startswith('https://'):
                colab_url = f'https://{colab_url}'

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

                # --- デバッグ: 復号画像の保存 ---
                debug_image_path = os.path.join(
                    settings.MEDIA_ROOT, 'debug_images', f'decoded_{safe_filename}')
                os.makedirs(os.path.dirname(debug_image_path), exist_ok=True)
                cv2.imwrite(debug_image_path, img)
                print(f"[DEBUG] デコードされた画像を保存しました: {debug_image_path}")
                print(f"[DEBUG] デコードされた画像の形状: {img.shape}")
                # --- デバッグ終了 ---

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
                        import unicodedata
                        for item_data in parsed_data['items']:
                            # 商品名が空の場合はスキップ
                            if not item_data.get('name'):
                                continue

                            product, created = Product.objects.get_or_create(
                                name=item_data['name']
                            )
                            receipt_item = ReceiptItem(
                                receipt=receipt,
                                product=product,
                                # quantityがない場合のデフォルト値
                                quantity=item_data.get('quantity', 1),
                                # priceがない場合のデフォルト値
                                price=item_data.get('price', 0)
                            )

                            # ポイント加算ロジック
                            item_points = 0
                            # まだこの商品でポイント加算していなければ処理
                            if product.id not in processed_products:
                                # 商品名を正規化（NFKC）して空白削除、小文字化
                                normalized_product_name = re.sub(r'\s+', '', unicodedata.normalize('NFKC', product.name)).lower()
                                
                                for eco_product in eco_products:
                                    # エコ商品名も同様に正規化
                                    normalized_eco_name = re.sub(r'\s+', '', unicodedata.normalize('NFKC', eco_product.name)).lower()
                                    
                                    # 商品名にエコ商品のキーワードが含まれているかチェック
                                    if normalized_eco_name in normalized_product_name:
                                        # 共通商品 または レシートの店舗とエコ商品の店舗が一致する場合のみ付与
                                        if eco_product.is_common or (receipt.store and eco_product.store == receipt.store):
                                            item_points = eco_product.points * receipt_item.quantity # 数量分ポイント加算
                                            total_eco_points_to_add += item_points
                                            processed_products.add(product.id)
                                            # 1つの商品が複数のエコ商品にマッチしても、最初の1つで抜ける
                                            break
                            
                            receipt_item.points = item_points
                            receipt_item.save()

                    # 合計ポイントを加算してユーザー情報を更新
                    if total_eco_points_to_add > 0:
                        user = request.user
                        user.add_points(total_eco_points_to_add)
                        
                        # レシートにも獲得ポイントを保存
                        receipt.points_earned = total_eco_points_to_add
                        receipt.save()

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
    # 1. 対象月の決定
    today = timezone.now()
    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
    except (ValueError, TypeError):
        year = today.year
        month = today.month

    # 年の検証 (datetimeの安全な範囲)
    if not (2000 <= year <= 2100):
        year = today.year

    # 月の正規化
    if month < 1:
        month = 12
        year -= 1
    elif month > 12:
        month = 1
        year += 1

    # 未来の月へのアクセスを制限
    if year > today.year or (year == today.year and month > today.month):
        year = today.year
        month = today.month

    is_latest_month = (year == today.year and month == today.month)
    
    # 2. レシートのフィルタリング
    # scanned_at is DateField
    start_date = datetime(year, month, 1).date()
    last_day = calendar.monthrange(year, month)[1]
    end_date = datetime(year, month, last_day).date()
    
    receipts = Receipt.objects.filter(
        user=request.user,
        scanned_at__range=(start_date, end_date)
    )
    
    # 3. 商品の集計とスコア計算
    purchased_products_display = []
    total_quantity = 0
    total_eco_points = 0
    eco_quantity = 0
    
    # エコ商品リストを取得
    eco_product_names = list(EcoProduct.objects.values_list('name', flat=True))
    
    # エコ商品マップを正規化して作成 (名前 -> ポイント)
    import unicodedata
    eco_product_normalized_map = {
        re.sub(r'\s+', '', unicodedata.normalize('NFKC', name)).lower(): points 
        for name, points in EcoProduct.objects.values_list('name', 'points')
    }

    for receipt in receipts:
        # ReceiptItemを優先
        items = receipt.items.all()
        if items.exists():
            for item in items:
                qty = item.quantity
                total_quantity += qty
                purchased_products_display.append(f"{item.product.name} ({qty}点)")
                
                # エコ商品チェック（正規化して比較）
                normalized_item_name = re.sub(r'\s+', '', unicodedata.normalize('NFKC', item.product.name)).lower()
                
                for eco_name_normalized, points in eco_product_normalized_map.items():
                    if eco_name_normalized in normalized_item_name:
                        eco_quantity += qty
                        total_eco_points += qty * points
                        break # 1つの商品が複数のエコ商品にマッチしても最初の一つで抜ける
                    
        # parsed_dataへのフォールバック
        elif receipt.parsed_data and isinstance(receipt.parsed_data, dict) and 'items' in receipt.parsed_data:
             for item_data in receipt.parsed_data['items']:
                 name = item_data.get('name', 'Unknown')
                 qty = item_data.get('quantity', 1)
                 total_quantity += qty
                 purchased_products_display.append(f"{name} ({qty}点)")
                 
                 # エコ商品チェック（正規化して比較）
                 normalized_item_name = re.sub(r'\s+', '', unicodedata.normalize('NFKC', name)).lower()

                 for eco_name_normalized, points in eco_product_normalized_map.items():
                    if eco_name_normalized in normalized_item_name:
                        eco_quantity += qty
                        total_eco_points += qty * points
                        break
    
    # 月間獲得ポイントの計算
    from django.db.models import Sum
    monthly_receipts = Receipt.objects.filter(
        user=request.user,
        scanned_at__year=year,
        scanned_at__month=month
    )
    calculated_monthly_points = monthly_receipts.aggregate(Sum('points_earned'))['points_earned__sum'] or 0
    current_rank_display = request.user.get_rank_display()

    # 既存レポートのチェック
    existing_report = Report.objects.filter(
        user=request.user,
        generated_at__year=year,
        generated_at__month=month
    ).first()

    report_text = ""
    score = 0
    report_exists = False
    
    # 表示用のランクとポイント（初期値は計算値/現在値）
    display_rank = current_rank_display
    display_monthly_points = calculated_monthly_points

    if existing_report:
        report_text = existing_report.description
        score = existing_report.score
        report_exists = True
        
        # レポートに保存された値があればそれを使う（アーカイブとしての役割）
        if existing_report.rank:
            display_rank = existing_report.rank
        if existing_report.monthly_points is not None:
             display_monthly_points = existing_report.monthly_points
    
    # 生成リクエストの処理
    elif request.method == 'POST' and 'generate' in request.POST:
        # スコア計算 (加重)
        if total_quantity > 0:
            raw_score = (total_eco_points / (total_quantity * 10)) * 100
            score = int(min(raw_score, 100)) # 100点キャップ
        else:
            score = 0
        
        if purchased_products_display:
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model = genai.GenerativeModel('gemini-flash-latest')
                
                # ユーザー入力のサニタイズ
                safe_products = purchased_products_display
                safe_eco_products = eco_product_names

                prompt = f"""
                あなたは環境保護のエキスパートです。
                ユーザーの今月のエコスコアは【{score}点】です。
                （購入商品数: {total_quantity}点、うちエコ商品: {eco_quantity}点、獲得エコポイント: {total_eco_points}点）
                
                以下の購入商品リストとエコ商品データベースを参考に、
                ユーザーに向けて**100文字程度**で簡潔なアドバイス付きレポートを作成してください。
                JSONではなく、テキストのみで出力してください。

                ※購入商品リストはレシートOCRの結果であり、省略や誤字が含まれる可能性があります。
                文脈から正式な商品名を推測し、どのような商品を購入したかを理解した上でアドバイスを行ってください。
                
                # 購入商品リスト:
                \"\"\"
                {', '.join(safe_products)}
                \"\"\"
                
                # エコ商品データベース:
                \"\"\"
                {', '.join(safe_eco_products)}
                \"\"\"
                """
                
                response = model.generate_content(prompt)
                report_text = response.text.strip()
                
                # レポート保存
                Report.objects.create(
                    user=request.user,
                    description=report_text,
                    score=score,
                    rank=current_rank_display,
                    monthly_points=calculated_monthly_points
                )
                report_exists = True
                
                # 表示用変数の更新は不要（初期値と同じ）

            except Exception as e:
                print(f"Gemini API Error: {e}")
                report_text = "AIレポートの生成中にエラーが発生しました。時間をおいて再度お試しください。"
        else:
            report_text = "今月の購入履歴がありません。"

    # 月間平均スコアの計算
    from django.db.models import Avg
    avg_score_data = Report.objects.filter(
        generated_at__year=year,
        generated_at__month=month
    ).aggregate(Avg('score'))
    average_score = avg_score_data['score__avg']
    if average_score is not None:
        average_score = round(average_score, 1)
    else:
        average_score = 0

    context = {
        'year': year,
        'month': month,
        'score': score,
        'report_text': report_text,
        'purchased_products': purchased_products_display,
        'eco_products': eco_product_names,
        'report_exists': report_exists,
        'average_score': average_score,
        'is_latest_month': is_latest_month,
        'rank': display_rank,
        'monthly_points': display_monthly_points,
    }
    return render(request, "core/ai_report.html", context)

# --- 問い合わせ関連ビュー ---


from core.services import InquiryService

def inquiry(request):
    if request.method == "POST":
        action = request.POST.get('action', 'confirm')

        if action == 'confirm':
            form = InquiryForm(request.POST, request.FILES)
            if form.is_valid():
                # サービス層で確認ステップ処理（画像一時保存など）
                context = InquiryService.handle_confirm_step(request, form)
                return render(request, "core/inquiry_confirm.html", context)
        
        elif action == 'back':
            initial_data = {
                'reply_to_email': request.POST.get('reply_to_email'),
                'subject': request.POST.get('subject'),
                'body_text': request.POST.get('body_text'),
            }
            form = InquiryForm(initial=initial_data)
            return render(request, "core/inquiry.html", {"form": form})

        elif action == 'send':
            data = {
                'reply_to_email': request.POST.get('reply_to_email'),
                'subject': request.POST.get('subject'),
                'body_text': request.POST.get('body_text'),
            }
            temp_image_name = request.POST.get('temp_image_name')
            
            try:
                # サービス層で作成
                InquiryService.create_inquiry(request.user, data, temp_image_name)
                return redirect("core:inquiry_complete")
            except ValueError:
                # バリデーションエラーなどで失敗した場合
                form = InquiryForm(data)
                return render(request, "core/inquiry.html", {"form": form})

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
        form = GrantCouponForm(request.POST, request_user=request.user)
        if form.is_valid():
            coupon = form.cleaned_data['coupon']
            target_all = form.cleaned_data['target_all']
            
            if target_all:
                # 全ユーザーのうち、必要ポイントを満たしているユーザーを取得
                required_points = coupon.required_points
                users = CustomUser.objects.filter(role='user', current_points__gte=required_points)
                
                count = 0
                skip_count = 0
                for user in users:
                    if user.current_coupons.filter(pk=coupon.pk).exists():
                        skip_count += 1
                    else:
                        user.current_coupons.add(coupon)
                        count += 1
                
                msg = f'条件（{required_points}pt以上）を満たす{count}人のユーザーにクーポン「{coupon.title}」を付与しました。'
                if skip_count > 0:
                    msg += f'（{skip_count}人は既に所持していたためスキップ）'
                messages.success(request, msg)
                
            else:
                user = form.cleaned_data['user']
                if user.current_coupons.filter(pk=coupon.pk).exists():
                    messages.warning(
                        request, f'ユーザー「{user.username}」は既にクーポン「{coupon.title}」を所持しています。')
                else:
                    user.current_coupons.add(coupon)
                    messages.success(
                        request, f'ユーザー「{user.username}」にクーポン「{coupon.title}」を付与しました。')
            
            return redirect('core:grant_coupon_admin')
    else:
        form = GrantCouponForm(request_user=request.user)
    return render(request, 'admin/grant_coupon_admin.html', {'form': form})


@staff_member_required
def announcement_detail(request, announcement_id):
    announcement = get_object_or_404(Announcement, pk=announcement_id)
    return render(request, 'admin/announcement_detail.html', {'announcement': announcement})


@staff_member_required
def admin_inquiry_dashboard(request):
    # ダッシュボード表示時に自動でメールを取り込む
    from core.utils import fetch_emails_from_gmail
    fetch_emails_from_gmail() # 結果はメッセージ表示せず、静かに更新する（またはログに出すだけでも良いが、今回はサイレント実行）

    status = request.GET.get('status', 'unanswered')
    if status not in ['unanswered', 'in_progress', 'completed']:
        status = 'unanswered'
    
    inquiries = Inquiry.objects.filter(status=status).order_by('-id')
    return render(request, 'admin/inquiry_dashboard.html', {
        'inquiries': inquiries,
        'current_status': status
    })


@staff_member_required
def inquiry_detail(request, inquiry_id):
    inquiry = get_object_or_404(Inquiry, id=inquiry_id)
    messages_list = inquiry.messages.all().order_by('created_at')

    if request.method == 'POST':
        # 完了ボタンが押された場合
        if 'complete' in request.POST:
            inquiry.status = 'completed'
            inquiry.save()
            messages.success(request, 'お問い合わせを完了としました。')
            return redirect('core:admin_inquiry_dashboard')
            
        form = ReplyForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            
            try:
                # サービス層で返信処理
                InquiryService.reply_to_inquiry(inquiry, subject, message)
                messages.success(request, '返信メールを送信しました。')
                return redirect('core:inquiry_detail', inquiry_id=inquiry.id)

            except Exception as e:
                print(f"Email send error: {e}")
                messages.error(request, 'メール送信に失敗しました。')

    else:
        # 返信フォームの初期値設定（件名にRe:をつける）
        initial_subject = f"Re: {inquiry.subject}" if not inquiry.subject.startswith("Re:") else inquiry.subject
        form = ReplyForm(initial={'subject': initial_subject})

    return render(request, 'admin/inquiry_detail.html', {
        'inquiry': inquiry, 
        'form': form,
        'messages_list': messages_list
    })


@login_required
def staff_index(request):
    announcements = Announcement.objects.all().order_by('-created_at')
    
    # クーポン統計の計算
    coupons = Coupon.objects.all()
    coupon_stats = []
    
    for coupon in coupons:
        # 現在の所持者数
        holders_count = coupon.customuser_set.count()
        # 利用回数
        usage_count = CouponUsage.objects.filter(coupon=coupon).count()
        # 発行総数 = 所持者数 + 利用回数
        issued_count = holders_count + usage_count
        
        # 利用率
        usage_ratio = 0
        if issued_count > 0:
            usage_ratio = (usage_count / issued_count) * 100
            
        # 自店での利用数
        used_at_my_store = 0
        if request.user.role == 'store' and request.user.store:
            used_at_my_store = CouponUsage.objects.filter(
                coupon=coupon, 
                store=request.user.store
            ).count()
        elif request.user.role == 'admin' or request.user.is_superuser:
            # 管理者の場合は全店舗での利用数を表示するか、あるいは「-」とするか
            # ここでは便宜上、全利用数を表示しておくか、0にしておく
            used_at_my_store = usage_count

        coupon_stats.append({
            'coupon': coupon,
            'issued_count': issued_count,
            'usage_count': usage_count,
            'usage_ratio': round(usage_ratio, 1),
            'used_at_my_store': used_at_my_store
        })

    return render(request, "admin/staff_index.html", {
        'announcements': announcements,
        'coupon_stats': coupon_stats
    })


@staff_member_required
def coupon_stats_detail(request, coupon_id):
    coupon = get_object_or_404(Coupon, pk=coupon_id)
    
    # 利用履歴の取得
    usage_history = CouponUsage.objects.filter(coupon=coupon).select_related('user', 'store').order_by('-used_at')
    
    # 店舗スタッフの場合は自店の利用履歴のみに絞り込む
    if request.user.role == 'store' and request.user.store:
        usage_history = usage_history.filter(store=request.user.store)
    
    # グラフ用データの作成
    chart_labels = []
    chart_data = []
    
    if request.user.role == 'store' and request.user.store:
        # 店舗スタッフ: ランクごとの利用割合
        from django.db.models import Count
        rank_stats = usage_history.values('user__rank').annotate(count=Count('id'))
        
        # ランク名のマッピング
        rank_names = dict(CustomUser.RANK_CHOICES)
        
        for stat in rank_stats:
            rank_code = stat['user__rank']
            count = stat['count']
            chart_labels.append(rank_names.get(rank_code, rank_code))
            chart_data.append(count)
            
    else:
        # 管理者: 店舗ごとの利用割合
        from django.db.models import Count
        store_stats = usage_history.values('store__store_name').annotate(count=Count('id'))
        
        for stat in store_stats:
            store_name = stat['store__store_name'] or '不明/オンライン'
            count = stat['count']
            chart_labels.append(store_name)
            chart_data.append(count)
            
    # 発行状況データの作成 (外側のリング用)
    # 利用済み総数
    global_usage_count = CouponUsage.objects.filter(coupon=coupon).count()
    # 未利用（現在所持しているユーザー数）
    holders_count = coupon.customuser_set.count()
    issued_chart_data = [global_usage_count, holders_count]

    import json
    context = {
        'coupon': coupon,
        'usage_history': usage_history,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
        'issued_chart_data': json.dumps(issued_chart_data),
        'is_store_staff': request.user.role == 'store'
    }
    return render(request, "admin/coupon_stats_detail.html", context)


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
class StoreEcoProductUpdateView(LoginRequiredMixin, UpdateView):
    model = EcoProduct
    form_class = StoreEcoProductForm
    template_name = 'core/store/product_form.html'
    success_url = reverse_lazy('core:store_dashboard')

    def get_queryset(self):
        # 自店舗の商品のみ編集可能
        if not self.request.user.store:
            return EcoProduct.objects.none()
        return EcoProduct.objects.filter(store=self.request.user.store)

    def form_valid(self, form):
        # 更新時にステータスを申請中に戻す（再申請）
        if self.object.status == 'rejected':
            form.instance.status = 'pending'
            form.instance.rejection_reason = ''  # 理由をクリア
            messages.info(self.request, '修正内容で再申請しました。')
        else:
            messages.success(self.request, 'エコ商品を更新しました。')
        return super().form_valid(form)


class StoreCouponUpdateView(LoginRequiredMixin, UpdateView):
    model = Coupon
    form_class = StoreCouponForm
    template_name = 'core/store/coupon_form.html'
    success_url = reverse_lazy('core:store_dashboard')

    def get_queryset(self):
        # 自店舗のクーポンのみ編集可能
        if not self.request.user.store:
            return Coupon.objects.none()
        return Coupon.objects.filter(store=self.request.user.store)

    def form_valid(self, form):
        # 更新時にステータスを申請中に戻す（再申請）
        if self.object.status == 'rejected':
            form.instance.status = 'pending'
            form.instance.rejection_reason = ''  # 理由をクリア
            messages.info(self.request, '修正内容で再申請しました。')
        else:
            messages.success(self.request, 'クーポンを更新しました。')
        return super().form_valid(form)


class StoreEcoProductDeleteView(LoginRequiredMixin, DeleteView):
    model = EcoProduct
    success_url = reverse_lazy('core:store_dashboard')
    
    def get_queryset(self):
        if not self.request.user.store:
            return EcoProduct.objects.none()
        return EcoProduct.objects.filter(store=self.request.user.store)

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'エコ商品を削除しました。')
        return super().delete(request, *args, **kwargs)


class StoreEcoProductDeleteView(LoginRequiredMixin, DeleteView):
    model = EcoProduct
    template_name = 'core/store/product_confirm_delete.html'
    success_url = reverse_lazy('core:store_dashboard')
    
    def get_queryset(self):
        if not self.request.user.store:
            return EcoProduct.objects.none()
        # 自店舗の商品はステータスに関わらず削除可能とする
        return EcoProduct.objects.filter(store=self.request.user.store)

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'エコ商品を削除しました。')
        return super().delete(request, *args, **kwargs)


@method_decorator(staff_member_required, name='dispatch')
class EcoProductListView(ListView):
    model = EcoProduct
    template_name = 'admin/ecoproduct_list.html'
    context_object_name = 'ecoproducts'

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.role == 'store' and user.store:
            # 共通商品 または 自店の申請商品（ただし却下を除く）
            return queryset.filter(
                (models.Q(is_common=True) | models.Q(store=user.store)) & ~models.Q(status='rejected')
            )
        # 管理者側も却下済みの商品は表示しない
        return queryset.exclude(status='rejected')


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


# --- 店舗申請・承認フロー関連ビュー ---

@login_required
def store_dashboard(request):
    if request.user.role != 'store' or not request.user.store:
        return redirect('core:index')
    
    # 自店舗の申請済みアイテム または 共通商品 を取得
    products = EcoProduct.objects.filter(
        (models.Q(store=request.user.store) | models.Q(is_common=True))
    ).order_by('-id')
    coupons = Coupon.objects.filter(store=request.user.store).order_by('-id')
    
    return render(request, 'core/store/dashboard.html', {
        'products': products,
        'coupons': coupons,
    })


@method_decorator(login_required, name='dispatch')
class StoreEcoProductCreateView(CreateView):
    model = EcoProduct
    form_class = StoreEcoProductForm
    template_name = 'core/store/product_form.html'
    success_url = reverse_lazy('core:store_dashboard')

    def dispatch(self, request, *args, **kwargs):
        if request.user.role != 'store' or not request.user.store:
            return redirect('core:index')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.store = self.request.user.store
        form.instance.status = 'pending'
        messages.success(self.request, 'エコ商品の登録申請を行いました。承認をお待ちください。')
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class StoreCouponCreateView(CreateView):
    model = Coupon
    form_class = StoreCouponForm
    template_name = 'core/store/coupon_form.html'
    success_url = reverse_lazy('core:store_dashboard')

    def dispatch(self, request, *args, **kwargs):
        if request.user.role != 'store' or not request.user.store:
            return redirect('core:index')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        with transaction.atomic():
            form.instance.store = self.request.user.store
            form.instance.status = 'pending'
            self.object = form.save()
            # 利用可能店舗に自店舗のみ追加
            self.object.available_stores.add(self.request.user.store)
            
        messages.success(self.request, 'クーポンの発行申請を行いました。承認をお待ちください。')
        return redirect(self.success_url)


@staff_member_required
def approval_list(request):
    # 申請中（pending）のアイテムを取得
    products = EcoProduct.objects.filter(status='pending').order_by('id')
    # 承認申請中または削除申請中のクーポンを取得
    coupons = Coupon.objects.filter(models.Q(status='pending') | models.Q(status='deletion_requested')).order_by('id')
    
    return render(request, 'core/admin/approval_list.html', {
        'products': products,
        'coupons': coupons,
    })


@login_required
def store_request_coupon_delete(request, coupon_id):
    if request.user.role != 'store' or not request.user.store:
        return redirect('core:index')
        
    coupon = get_object_or_404(Coupon, id=coupon_id, store=request.user.store)
    
    if request.method == 'POST':
        coupon.status = 'deletion_requested'
        coupon.save()
        messages.success(request, f'{coupon.title} の削除申請を行いました。')
        
    return redirect('core:store_dashboard')


@staff_member_required
def approve_item(request, type, id):
    if request.method == 'POST':
        if type == 'product':
            item = get_object_or_404(EcoProduct, id=id)
        elif type == 'coupon':
            item = get_object_or_404(Coupon, id=id)
        else:
            return redirect('core:approval_list')
        
        if type == 'coupon' and item.status == 'deletion_requested':
            item.delete()
            messages.success(request, f'クーポンを削除しました。')
        else:
            # エコ商品の承認時、共通フラグのチェックを確認
            if type == 'product' and request.POST.get('as_common'):
                item.is_common = True
                messages.success(request, f'{item} を【共通商品】として承認しました。')
            else:
                messages.success(request, f'{item} を承認しました。')
            
            item.status = 'approved'
            item.save()
        
    return redirect('core:approval_list')


@staff_member_required
def reject_item(request, type, id):
    if request.method == 'POST':
        if type == 'product':
            item = get_object_or_404(EcoProduct, id=id)
        elif type == 'coupon':
            item = get_object_or_404(Coupon, id=id)
        else:
            return redirect('core:approval_list')
        
        if type == 'coupon' and item.status == 'deletion_requested':
            item.status = 'approved' # 削除却下時は承認済みに戻す
            item.save()
            messages.warning(request, f'{item} の削除申請を却下しました（承認済みに戻しました）。')
        else:
            item.status = 'rejected'
            item.save()
            messages.warning(request, f'{item} を却下しました。')
        
    return redirect('core:approval_list')


from core.utils import fetch_emails_from_gmail

@staff_member_required
def fetch_emails(request):
    """手動メール取り込みビュー"""
    success, message = fetch_emails_from_gmail()
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    
    # 元のページに戻る（なければダッシュボード）
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('core:admin_inquiry_dashboard')
