import json
from django.core.management.base import BaseCommand
from core.views import parse_receipt_data

class Command(BaseCommand):
    help = 'RECIPT.TXTを使用してレシート解析ロジックをテストします。'

    def handle(self, *args, **options):
        try:
            with open('RECIPT.TXT', 'r', encoding='utf-8') as f:
                receipt_text = f.read()
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR('RECIPT.TXT がルートディレクトリに見つかりません。'))
            return

        # 実際のレシートテキストの開始位置を検索
        start_keyword = '元の文字起こし結果を表示'
        if start_keyword in receipt_text:
            receipt_text = receipt_text.split(start_keyword, 1)[1]

        self.stdout.write("--- 改良されたロジックで RECIPT.TXT を解析中 ---")
        
        parsed_data = parse_receipt_data(receipt_text)
        
        # JSONシリアライズ用に日時を文字列変換
        if parsed_data.get('transaction_time'):
            parsed_data['transaction_time'] = parsed_data['transaction_time'].isoformat()

        self.stdout.write(self.style.SUCCESS("解析完了。結果:"))
        
        # JSON形式で出力
        self.stdout.write(json.dumps(parsed_data, indent=2, ensure_ascii=False))

        # 商品サマリーを出力
        self.stdout.write("\n--- 商品サマリー ---")
        if parsed_data.get('items'):
            for item in parsed_data['items']:
                self.stdout.write(
                    f"  - Name: {item.get('name', 'N/A')}, "
                    f"Quantity: {item.get('quantity', 'N/A')}, "
                    f"Price: {item.get('price', 'N/A')}"
                )
        else:
            self.stdout.write("商品が抽出されませんでした。")
        
        self.stdout.write("\n--- テスト終了 ---")

