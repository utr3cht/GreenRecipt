import json
from django.core.management.base import BaseCommand
from core.views import parse_receipt_data

class Command(BaseCommand):
    help = 'Tests the receipt parsing logic with RECIPT.TXT'

    def handle(self, *args, **options):
        try:
            with open('RECIPT.TXT', 'r', encoding='utf-8') as f:
                receipt_text = f.read()
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR('RECIPT.TXT not found in the root directory.'))
            return

        # Find the start of the actual receipt text
        start_keyword = '元の文字起こし結果を表示'
        if start_keyword in receipt_text:
            receipt_text = receipt_text.split(start_keyword, 1)[1]

        self.stdout.write("--- Parsing RECIPT.TXT with the improved logic ---")
        
        parsed_data = parse_receipt_data(receipt_text)
        
        # Convert datetime to string for JSON serialization
        if parsed_data.get('transaction_time'):
            parsed_data['transaction_time'] = parsed_data['transaction_time'].isoformat()

        self.stdout.write(self.style.SUCCESS("Parsing complete. Here is the result:"))
        
        # Pretty print the JSON-like structure
        self.stdout.write(json.dumps(parsed_data, indent=2, ensure_ascii=False))

        # Also print a summary of items
        self.stdout.write("\n--- Summary of Items ---")
        if parsed_data.get('items'):
            for item in parsed_data['items']:
                self.stdout.write(
                    f"  - Name: {item.get('name', 'N/A')}, "
                    f"Quantity: {item.get('quantity', 'N/A')}, "
                    f"Price: {item.get('price', 'N/A')}"
                )
        else:
            self.stdout.write("No items were extracted.")
        
        self.stdout.write("\n--- End of Test ---")

