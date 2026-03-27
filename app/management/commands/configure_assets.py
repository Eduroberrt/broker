from django.core.management.base import BaseCommand
from app.models import CryptoAsset

class Command(BaseCommand):
    help = 'Configure asset types and watchlist settings'

    def handle(self, *args, **options):
        # Coins with addresses - should be in watchlist
        watchlist_symbols = ['BTC', 'XRP', 'XLM', 'Hedera']  # Note: HBAR's symbol in DB is 'Hedera'
        
        # Stock assets
        stock_assets = ['Tesla xStock', 'SpaceXAI', 'Paimon SpaceX SPV']
        
        # Update all assets
        assets = CryptoAsset.objects.all()
        
        for asset in assets:
            # Set watchlist
            if asset.symbol in watchlist_symbols:
                asset.is_in_watchlist = True
                self.stdout.write(self.style.SUCCESS(f'✓ {asset.name} ({asset.symbol}) added to watchlist'))
            else:
                asset.is_in_watchlist = False
                self.stdout.write(f'  {asset.name} ({asset.symbol}) removed from watchlist')
            
            # Set asset type
            if asset.name in stock_assets:
                asset.asset_type = 'stock'
                self.stdout.write(self.style.SUCCESS(f'✓ {asset.name} set as stock'))
            else:
                asset.asset_type = 'crypto'
                self.stdout.write(f'  {asset.name} set as crypto')
            
            asset.save()
        
        self.stdout.write(self.style.SUCCESS('\n✓ Asset configuration complete!'))
        self.stdout.write(f'Watchlist: BTC, XRP, XLM, HBAR (Hedera)')
        self.stdout.write(f'Stocks: {", ".join(stock_assets)}')
