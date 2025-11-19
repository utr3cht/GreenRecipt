
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "GreenRecipt.settings")
django.setup()

from core.models import Inquiry

# 画像ファイル名が空文字列やNULLでないものを探す
inquiry = Inquiry.objects.exclude(image__isnull=True).exclude(image='').order_by('-id').first()

if inquiry:
  print(f"Inquiry ID: {inquiry.id}")
  print(f"Image Field Value: {inquiry.image}")
  print(f"Image URL: {inquiry.image.url}")
  print(f"Image Path: {inquiry.image.path}")
else:
  print("データベースに画像付きのお問い合わせデータが見つかりませんでした。")
  print("テストとして、まず画像付きのお問い合わせを一件作成してください。")
