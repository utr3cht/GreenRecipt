from django.core.management.base import BaseCommand
from core.models import Receipt
import json

class Command(BaseCommand):
    help = 'Displays the details of the most recently scanned receipt'

    def handle(self, *args, **kwargs):
        try:
            latest_receipt = Receipt.objects.latest('id')
            self.stdout.write(self.style.SUCCESS(f"--- 最新のレシート (ID: {latest_receipt.id}) の詳細 ---"))
            
            self.stdout.write(self.style.WARNING("\n[店舗]"))
            if latest_receipt.store:
                self.stdout.write(f"  - 関連付けられた店舗: {latest_receipt.store.store_name}")
            else:
                self.stdout.write("  - 関連付けられた店舗はありません")

            self.stdout.write(self.style.WARNING("\n[取引日時]"))
            if latest_receipt.transaction_time:
                self.stdout.write(f"  - 抽出された日時: {latest_receipt.transaction_time.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                self.stdout.write("  - 日時は抽出されませんでした")

            self.stdout.write(self.style.WARNING("\n[解析された商品データ (parsed_data)]"))
            if latest_receipt.parsed_data:
                self.stdout.write(json.dumps(latest_receipt.parsed_data, indent=2, ensure_ascii=False))
            else:
                self.stdout.write("  - 商品データは抽出されませんでした")

            self.stdout.write(self.style.WARNING("\n[元のOCRテキスト (ocr_text)]"))
            self.stdout.write("-" * 20)
            self.stdout.write(latest_receipt.ocr_text)
            self.stdout.write("-" * 20)

        except Receipt.DoesNotExist:
            self.stdout.write(self.style.ERROR("レシートデータが見つかりません。"))
