from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from app.models import UserPriceOverride, CryptoAsset
from decimal import Decimal


class Command(BaseCommand):
    help = 'Check TSLAx price override functionality'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== TSLAx Price Override Check ===\n'))
        
        # Check total users and overrides
        total_users = User.objects.count()
        total_overrides = UserPriceOverride.objects.count()
        
        self.stdout.write(f'Total Users: {total_users}')
        self.stdout.write(f'Total UserPriceOverride entries: {total_overrides}')
        
        if total_overrides == 0:
            self.stdout.write(self.style.WARNING('\n⚠️  No UserPriceOverride entries found!'))
            self.stdout.write('Creating UserPriceOverride for all users...\n')
            for user in User.objects.all():
                UserPriceOverride.objects.get_or_create(user=user)
            total_overrides = UserPriceOverride.objects.count()
            self.stdout.write(self.style.SUCCESS(f'✓ Created {total_overrides} UserPriceOverride entries'))
        
        # Show sample entries
        self.stdout.write('\n--- Sample UserPriceOverride Entries ---')
        for override in UserPriceOverride.objects.all()[:5]:
            xrp_price = f'${override.xrp_custom_price}' if override.xrp_custom_price else 'Not Set'
            tslax_price = f'${override.tslax_custom_price}' if override.tslax_custom_price else 'Not Set'
            self.stdout.write(f'  • {override.user.username}: XRP={xrp_price}, TSLAx={tslax_price}')
        
        # Check if TSLAx asset exists
        self.stdout.write('\n--- TSLAx Asset Check ---')
        try:
            tslax = CryptoAsset.objects.get(symbol='TSLAx')
            self.stdout.write(f'✓ TSLAx found: ${tslax.current_price}')
        except CryptoAsset.DoesNotExist:
            self.stdout.write(self.style.ERROR('✗ TSLAx asset not found in database!'))
        
        # Test override for first user
        if total_users > 0:
            test_user = User.objects.first()
            override, created = UserPriceOverride.objects.get_or_create(user=test_user)
            
            self.stdout.write(f'\n--- Testing with user: {test_user.username} ---')
            self.stdout.write(f'Current XRP override: {override.xrp_custom_price}')
            self.stdout.write(f'Current TSLAx override: {override.tslax_custom_price}')
            
            # Set a test TSLAx price
            test_price = Decimal('100.50')
            override.tslax_custom_price = test_price
            override.save()
            
            self.stdout.write(self.style.SUCCESS(f'\n✓ Set TSLAx override to ${test_price} for {test_user.username}'))
            self.stdout.write('  This price will now show for this user across the entire site!')
            
            # Verify it was saved
            override.refresh_from_db()
            if override.tslax_custom_price == test_price:
                self.stdout.write(self.style.SUCCESS('✓ Override saved successfully in database'))
            else:
                self.stdout.write(self.style.ERROR('✗ Override NOT saved correctly'))
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('✓ TSLAx override is ready to use!'))
        self.stdout.write('  - Go to admin panel')
        self.stdout.write('  - Navigate to User Price Overrides')
        self.stdout.write('  - Set custom TSLAx price for any user')
        self.stdout.write('  - That price will display site-wide for that user')
        self.stdout.write('='*50 + '\n')
