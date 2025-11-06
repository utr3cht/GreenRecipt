from django.core.management.base import BaseCommand
from core.models import Store

class Command(BaseCommand):
    help = 'Inserts initial store data into the database.'

    def handle(self, *args, **options):
        stores_data = [
            {
                'store_name': '青源味噌株式会社',
                'category': '味噌製造・販売（発酵食品・地産地消）',
                'tel': '028-622-8301',
                'address': '栃木県宇都宮市旭1-4-31',
                'open_hours': '9:00〜18:00',
                'lat': 0.0,
                'lng': 0.0
            },
            {
                'store_name': '株式会社アキモ',
                'category': '漬物製造（フードロス削減・地域農産物活用）',
                'tel': '028-648-5111',
                'address': '栃木県宇都宮市平出工業団地15-8',
                'open_hours': '8:30〜17:30',
                'lat': 0.0,
                'lng': 0.0
            },
            {
                'store_name': '株式会社ヨークベニマル宇都宮店',
                'category': 'スーパーマーケット（地場野菜販売・リサイクル推進）',
                'tel': '028-634-7011',
                'address': '栃木県宇都宮市陽東6-2-1',
                'open_hours': '9:00〜21:00',
                'lat': 0.0,
                'lng': 0.0
            },
            {
                'store_name': '株式会社グリーンデイズ',
                'category': '農産物直売所運営（「農産物直売所あぜみち」運営）',
                'tel': '028-660-1122',
                'address': '栃木県宇都宮市上戸祭町3031-3',
                'open_hours': '9:00〜18:00',
                'lat': 0.0,
                'lng': 0.0
            },
            {
                'store_name': '有限会社金田昇商店',
                'category': '食鳥肉・調理食品販売',
                'tel': '028-634-5454',
                'address': '栃木県宇都宮市本町6-10',
                'open_hours': '8:00〜18:00',
                'lat': 0.0,
                'lng': 0.0
            },
            {
                'store_name': '阿部梨園',
                'category': '果樹園・直売（フードロス・堆肥循環）',
                'tel': '028-669-2528',
                'address': '栃木県宇都宮市上籠谷町254',
                'open_hours': '9:00〜17:00',
                'lat': 0.0,
                'lng': 0.0
            },
            {
                'store_name': '有限会社メルシー',
                'category': '洋菓子製造販売・カフェ',
                'tel': '028-635-9020',
                'address': '栃木県宇都宮市砥上町795-4',
                'open_hours': '10:00〜19:00',
                'lat': 0.0,
                'lng': 0.0
            },
            {
                'store_name': '有限会社マルシン靴店',
                'category': '靴販売・修理（リペア推奨）',
                'tel': '028-633-6050',
                'address': '栃木県宇都宮市西1-2-2',
                'open_hours': '12:30〜19:30',
                'lat': 0.0,
                'lng': 0.0
            },
            {
                'store_name': '株式会社村上酒店',
                'category': '地酒販売（地産地消・リターナブル瓶推奨）',
                'tel': '028-670-8899',
                'address': '栃木県宇都宮市板戸町360-3',
                'open_hours': '9:00〜18:00',
                'lat': 0.0,
                'lng': 0.0
            },
            {
                'store_name': 'ガンダラカフェ',
                'category': 'カフェ・居場所スペース',
                'tel': '028-612-6735',
                'address': '栃木県宇都宮市江野町11-6 むぎくら中央ビル2F-B',
                'open_hours': '11:00〜19:00',
                'lat': 0.0,
                'lng': 0.0
            },
            {
                'store_name': 'グランディハウス株式会社',
                'category': '住宅建設・販売',
                'tel': '028-650-7777',
                'address': '栃木県宇都宮市大通り4-3-18',
                'open_hours': '9:00〜18:00',
                'lat': 0.0,
                'lng': 0.0
            },
            {
                'store_name': '株式会社カナメ',
                'category': '金属屋根・太陽光発電・社寺建築',
                'tel': '028-663-6300',
                'address': '栃木県宇都宮市平出工業団地38-52',
                'open_hours': '9:00〜18:00',
                'lat': 0.0,
                'lng': 0.0
            },
            {
                'store_name': '環境整備株式会社',
                'category': '総合施設管理・ビルメンテナンス',
                'tel': '028-664-3711',
                'address': '栃木県宇都宮市岩曽町1333',
                'open_hours': '8:30〜17:30',
                'lat': 0.0,
                'lng': 0.0
            },
        ]

        for data in stores_data:
            # Check if a store with the same name and address already exists
            if not Store.objects.filter(store_name=data['store_name'], address=data['address']).exists():
                Store.objects.create(**data)
                self.stdout.write(self.style.SUCCESS(f"Successfully added store: {data['store_name']}"))
            else:
                self.stdout.write(self.style.WARNING(f"Store already exists, skipping: {data['store_name']}"))

        self.stdout.write(self.style.SUCCESS('Initial store data insertion complete.'))
