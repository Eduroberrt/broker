from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from app.models import CryptoAsset, UserWallet

class Command(BaseCommand):
    help = 'Create wallet entries for all users and all cryptocurrencies with 0 balance'

    def handle(self, *args, **options):
        users = User.objects.all()
        crypto_assets = CryptoAsset.objects.all()
        
        if not users.exists():
            self.stdout.write(self.style.WARNING('No users found in database'))
            return
        
        if not crypto_assets.exists():
            self.stdout.write(self.style.WARNING('No crypto assets found in database'))
            return
        
        created_count = 0
        existing_count = 0
        
        self.stdout.write(f'\n🔄 Creating wallets for {users.count()} users and {crypto_assets.count()} cryptocurrencies...\n')
        
        for user in users:
            for crypto in crypto_assets:
                wallet, created = UserWallet.objects.get_or_create(
                    user=user,
                    crypto_asset=crypto,
                    defaults={'balance': 0}
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Created: {user.username} - {crypto.symbol} ($0.00)')
                    )
                else:
                    existing_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ Summary:')
        )
        self.stdout.write(f'   • Created: {created_count} new wallets')
        self.stdout.write(f'   • Existing: {existing_count} wallets')
        self.stdout.write(f'   • Total: {created_count + existing_count} wallets')
        self.stdout.write('\nAdmin can now view and manipulate all user balances in User Wallets section.')
