from django.core.management.base import BaseCommand
from app.models import CryptoAsset


class Command(BaseCommand):
    help = 'Populate initial cryptocurrency data'

    def handle(self, *args, **options):
        crypto_data = [
            {
                'name': 'Bitcoin',
                'symbol': 'BTC',
                'icon': '₿',
                'color': '#f7931a',
                'current_price': 42850.00,
                'base_price': 40700.00,
                'order': 1
            },
            {
                'name': 'Ripple',
                'symbol': 'XRP',
                'icon': 'X',
                'color': '#2563eb',
                'current_price': 0.6420,
                'base_price': 0.6190,
                'order': 2
            },
            {
                'name': 'Stellar',
                'symbol': 'XLM',
                'icon': '*',
                'color': '#06b6d4',
                'current_price': 0.1245,
                'base_price': 0.1264,
                'order': 3
            },
            {
                'name': 'Hedera',
                'symbol': 'HBAR',
                'icon': 'H',
                'color': '#9333ea',
                'current_price': 0.0875,
                'base_price': 0.0815,
                'order': 4
            },
        ]

        for data in crypto_data:
            crypto, created = CryptoAsset.objects.update_or_create(
                symbol=data['symbol'],
                defaults=data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created {crypto.name}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Updated {crypto.name}'))

        self.stdout.write(self.style.SUCCESS('Successfully populated crypto assets!'))
