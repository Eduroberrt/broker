from django.core.management.base import BaseCommand
from app.models import CryptoAsset
import requests
from decimal import Decimal
from datetime import datetime

class Command(BaseCommand):
    help = 'Update cryptocurrency prices from CoinGecko API (excludes XRP which is manually controlled)'

    # Map our symbols to CoinGecko IDs
    COINGECKO_MAP = {
        'BTC': 'bitcoin',
        'ETH': 'ethereum',
        'USDT': 'tether',
        'BNB': 'binancecoin',
        'SOL': 'solana',
        'USDC': 'usd-coin',
        'XLM': 'stellar',
        'HBAR': 'hedera-hashgraph',
        'Hedera': 'hedera-hashgraph',  # Alternative name
        'DOGE': 'dogecoin',
        'ADA': 'cardano',
        'AVAX': 'avalanche-2',
        'TRX': 'tron',
        'DOT': 'polkadot',
        'MATIC': 'polygon',
        'LTC': 'litecoin',
    }

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(f'\n🔄 Starting price update at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'))
        
        # Get all crypto assets except XRP (which is manually controlled)
        assets = CryptoAsset.objects.filter(asset_type='crypto').exclude(symbol='XRP')
        
        if not assets.exists():
            self.stdout.write(self.style.WARNING('No crypto assets found to update'))
            return
        
        # Prepare CoinGecko API request
        coingecko_ids = []
        symbol_to_id = {}
        
        for asset in assets:
            coingecko_id = self.COINGECKO_MAP.get(asset.symbol)
            if coingecko_id:
                coingecko_ids.append(coingecko_id)
                symbol_to_id[coingecko_id] = asset.symbol
            else:
                self.stdout.write(self.style.WARNING(f'⚠️  No CoinGecko mapping for {asset.symbol}'))
        
        if not coingecko_ids:
            self.stdout.write(self.style.WARNING('No valid CoinGecko IDs to fetch'))
            return
        
        # Fetch prices from CoinGecko API
        try:
            url = 'https://api.coingecko.com/api/v3/simple/price'
            params = {
                'ids': ','.join(coingecko_ids),
                'vs_currencies': 'usd',
                'include_24hr_change': 'true'
            }
            
            self.stdout.write(f'📡 Fetching prices for {len(coingecko_ids)} assets...')
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Update prices
            updated_count = 0
            for coingecko_id, price_data in data.items():
                symbol = symbol_to_id.get(coingecko_id)
                if not symbol:
                    continue
                
                try:
                    asset = CryptoAsset.objects.get(symbol=symbol)
                    new_price = Decimal(str(price_data['usd']))
                    old_price = asset.current_price
                    
                    # Update current price
                    asset.current_price = new_price
                    
                    # Optionally update base_price if you want to reset the percentage change reference
                    # For now, we'll keep base_price unchanged so percentage shows change from original base
                    
                    asset.save()
                    updated_count += 1
                    
                    change_indicator = '📈' if new_price > old_price else '📉' if new_price < old_price else '➡️'
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ {asset.name} ({symbol}): ${old_price:,.8f} → ${new_price:,.8f} {change_indicator}'
                        )
                    )
                    
                except CryptoAsset.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'⚠️  Asset {symbol} not found in database'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'❌ Error updating {symbol}: {str(e)}'))
            
            self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully updated {updated_count} of {len(coingecko_ids)} assets'))
            self.stdout.write(self.style.WARNING(f'ℹ️  XRP prices are manually controlled by admin'))
            
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f'❌ API request failed: {str(e)}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Unexpected error: {str(e)}'))
