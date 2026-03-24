from django.core.management.base import BaseCommand
from app.models import CryptoAsset

class Command(BaseCommand):
    help = 'Add popular crypto assets and custom tokens to the database'

    def handle(self, *args, **kwargs):
        assets = [
            # Existing popular cryptos - updating if needed
            {'name': 'Bitcoin', 'symbol': 'BTC', 'icon': '₿', 'color': '#f7931a', 'current_price': 67500.00, 'base_price': 65000.00, 'order': 1},
            {'name': 'Ethereum', 'symbol': 'ETH', 'icon': 'Ξ', 'color': '#627eea', 'current_price': 3500.00, 'base_price': 3400.00, 'order': 2},
            {'name': 'Tether', 'symbol': 'USDT', 'icon': '₮', 'color': '#26a17b', 'current_price': 1.00, 'base_price': 1.00, 'order': 3},
            {'name': 'BNB', 'symbol': 'BNB', 'icon': 'B', 'color': '#f3ba2f', 'current_price': 580.00, 'base_price': 565.00, 'order': 4},
            {'name': 'Solana', 'symbol': 'SOL', 'icon': 'S', 'color': '#00ffa3', 'current_price': 145.00, 'base_price': 135.00, 'order': 5},
            {'name': 'XRP', 'symbol': 'XRP', 'icon': 'X', 'color': '#23292f', 'current_price': 0.52, 'base_price': 0.50, 'order': 6},
            {'name': 'Cardano', 'symbol': 'ADA', 'icon': '₳', 'color': '#0033ad', 'current_price': 0.45, 'base_price': 0.43, 'order': 7},
            {'name': 'Dogecoin', 'symbol': 'DOGE', 'icon': 'Ð', 'color': '#c2a633', 'current_price': 0.12, 'base_price': 0.11, 'order': 8},
            {'name': 'Polkadot', 'symbol': 'DOT', 'icon': '●', 'color': '#e6007a', 'current_price': 7.50, 'base_price': 7.20, 'order': 9},
            {'name': 'Polygon', 'symbol': 'MATIC', 'icon': 'M', 'color': '#8247e5', 'current_price': 0.85, 'base_price': 0.82, 'order': 10},
            {'name': 'Litecoin', 'symbol': 'LTC', 'icon': 'Ł', 'color': '#345d9d', 'current_price': 85.00, 'base_price': 82.00, 'order': 11},
            {'name': 'Avalanche', 'symbol': 'AVAX', 'icon': 'A', 'color': '#e84142', 'current_price': 38.00, 'base_price': 36.00, 'order': 12},
            
            # New custom tokens
            {'name': 'Gold Coin', 'symbol': 'GOLD', 'icon': '◎', 'color': '#ffd700', 'current_price': 2150.00, 'base_price': 2100.00, 'order': 13},
            {'name': 'Tesla xStock', 'symbol': 'TSLA-X', 'icon': 'T', 'color': '#e82127', 'current_price': 245.00, 'base_price': 235.00, 'order': 14},
            {'name': 'SpaceXAI', 'symbol': 'SPXAI', 'icon': '🚀', 'color': '#005288', 'current_price': 12.50, 'base_price': 10.00, 'order': 15},
            {'name': 'Paimon SpaceX SPV', 'symbol': 'PAIMON', 'icon': '⭐', 'color': '#9d4edd', 'current_price': 8.75, 'base_price': 7.50, 'order': 16},
        ]
        
        created_count = 0
        updated_count = 0
        
        for asset_data in assets:
            asset, created = CryptoAsset.objects.update_or_create(
                symbol=asset_data['symbol'],
                defaults=asset_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Created: {asset.name} ({asset.symbol})'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'↻ Updated: {asset.name} ({asset.symbol})'))
        
        self.stdout.write(self.style.SUCCESS(f'\nSummary: {created_count} created, {updated_count} updated'))
