from django.core.management.base import BaseCommand
from app.models import CryptoAsset

class Command(BaseCommand):
    help = 'Set wallet addresses for the 4 watchlist coins (BTC, XRP, XLM, HBAR)'

    def handle(self, *args, **options):
        # Define wallet addresses for each coin
        wallet_addresses = {
            'BTC': 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
            'XRP': 'rDGrc3KfS776Qypy1bs3nJVHK824bHPNpi',
            'XLM': 'GDUVA2EXLVYVYERDHY2YH2WD7FGWXSWIKO342MYJWZX7CRCPLREYB22I',
            'Hedera': 'ksetjtEULES3WjRXZh3qJzzLYEaMNazjS9kb4cdM32F',  # HBAR uses Hedera as symbol in DB
        }
        
        updated_count = 0
        for symbol, address in wallet_addresses.items():
            try:
                asset = CryptoAsset.objects.get(symbol=symbol)
                asset.receive_wallet_address = address
                asset.save()
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ {asset.name} ({symbol}): {address}')
                )
            except CryptoAsset.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Asset {symbol} not found in database')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ Successfully set wallet addresses for {updated_count} coins')
        )
        self.stdout.write('These coins will now appear on Sell and Receive pages.')
