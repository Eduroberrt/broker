from django.core.management.base import BaseCommand
from app.models import CryptoAsset

class Command(BaseCommand):
    help = 'Update Tesla, Paimon, and ETH symbols and addresses'

    def handle(self, *args, **options):
        self.stdout.write('\n🔄 Updating asset symbols and addresses...\n')
        
        updates = []
        
        # 1. Update Tesla xStock symbol from TSLA-X to TSLAx
        try:
            tesla = CryptoAsset.objects.get(symbol='TSLA-X')
            tesla.symbol = 'TSLAx'
            tesla.receive_wallet_address = 'ksetjtEULES3WjRXZh3qJzzLYEaMNazjS9kb4cdM32F'
            tesla.save()
            updates.append(f'✓ Tesla xStock: Symbol updated to TSLAx, address added')
        except CryptoAsset.DoesNotExist:
            self.stdout.write(self.style.WARNING('⚠ Tesla xStock (TSLA-X) not found'))
        
        # 2. Update Paimon symbol from PAIMON to SPCX
        try:
            paimon = CryptoAsset.objects.get(symbol='PAIMON')
            paimon.symbol = 'SPCX'
            paimon.receive_wallet_address = '0x7b4Fe1E927a2Fa160848ec019B590069B5b28E80'
            paimon.save()
            updates.append(f'✓ Paimon SpaceX SPV: Symbol updated to SPCX, address added')
        except CryptoAsset.DoesNotExist:
            self.stdout.write(self.style.WARNING('⚠ Paimon (PAIMON) not found'))
        
        # 3. Add address to ETH
        try:
            eth = CryptoAsset.objects.get(symbol='ETH')
            eth.receive_wallet_address = '0x7b4Fe1E927a2Fa160848ec019B590069B5b28E80'
            eth.save()
            updates.append(f'✓ Ethereum (ETH): Address added')
        except CryptoAsset.DoesNotExist:
            self.stdout.write(self.style.WARNING('⚠ Ethereum (ETH) not found'))
        
        # Display results
        self.stdout.write('\n✅ Update Summary:')
        for update in updates:
            self.stdout.write(f'   {update}')
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully updated {len(updates)} assets'))
        self.stdout.write('\nℹ️  Addresses are now available in receive and sell pages.\n')
