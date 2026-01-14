
import os
from django.core.management.base import BaseCommand, CommandError
from core.models import Inquiry

class Command(BaseCommand):
    help = '指定された問い合わせの画像と詳細を確認します。'

    def add_arguments(self, parser):
        parser.add_argument('inquiry_id', type=int, help='確認する問い合わせID')

    def handle(self, *args, **options):
        inquiry_id = options['inquiry_id']
        try:
            inquiry = Inquiry.objects.get(pk=inquiry_id)
        except Inquiry.DoesNotExist:
            raise CommandError(f'問い合わせID "{inquiry_id}" は存在しません。')

        self.stdout.write(f"問い合わせID詳細確認: {inquiry.id}")
        self.stdout.write("-" * 30)

        if inquiry.image:
            self.stdout.write(self.style.SUCCESS(f"画像フィールドの値: {inquiry.image}"))
            
            # 1. Djangoの観点を出力
            try:
                image_url = inquiry.image.url
                self.stdout.write(f"  - Django生成URL (.url): {image_url}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  - .urlプロパティ取得失敗: {e}"))

            try:
                image_path = inquiry.image.path
                self.stdout.write(f"  - Django期待パス (.path): {image_path}")

                # 2. ファイルの実在確認
                if os.path.exists(image_path):
                    self.stdout.write(self.style.SUCCESS("  - ファイルは期待されるパスに存在します。"))
                else:
                    self.stdout.write(self.style.ERROR("  - ファイルが期待されるパスに存在しません。"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  - .pathプロパティ取得または存在確認失敗: {e}"))

        else:
            self.stdout.write(self.style.WARNING("この問い合わせには画像が関連付けられていません。"))
        
        self.stdout.write("-" * 30)
