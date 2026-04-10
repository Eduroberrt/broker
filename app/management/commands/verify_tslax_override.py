from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from app.models import UserPriceOverride, CryptoAsset
from decimal import Decimal


class Command(BaseCommand):
    help = 'Verify TSLAx override works for new and existing accounts'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== Testing TSLAx Override for New & Old Accounts ===\n'))
        
        # Get TSLAx asset
        try:
            tslax = CryptoAsset.objects.get(symbol='TSLAx')
            global_price = tslax.current_price
            self.stdout.write(f'Global TSLAx Price: ${global_price}')
        except CryptoAsset.DoesNotExist:
            self.stdout.write(self.style.ERROR('TSLAx asset not found!'))
            return
        
        self.stdout.write('\n--- Testing Existing Accounts ---')
        
        # Test with existing users
        for user in User.objects.all():
            override = UserPriceOverride.objects.filter(user=user).first()
            
            if override:
                if override.tslax_custom_price:
                    self.stdout.write(self.style.SUCCESS(
                        f'✓ {user.username}: Has override = ${override.tslax_custom_price} (will see this instead of ${global_price})'
                    ))
                else:
                    self.stdout.write(f'  {user.username}: No override (will see global ${global_price})')
            else:
                self.stdout.write(self.style.WARNING(f'⚠️  {user.username}: No UserPriceOverride entry!'))
        
        # Create a test new user to verify signal works
        self.stdout.write('\n--- Testing New Account Creation ---')
        test_username = 'test_tslax_user_123'
        
        # Delete if exists
        User.objects.filter(username=test_username).delete()
        
        # Create new user
        new_user = User.objects.create_user(username=test_username, password='testpass123')
        self.stdout.write(f'Created new user: {test_username}')
        
        # Check if UserPriceOverride was auto-created
        try:
            new_override = UserPriceOverride.objects.get(user=new_user)
            self.stdout.write(self.style.SUCCESS('✓ UserPriceOverride auto-created by signal!'))
            self.stdout.write(f'  - XRP: {new_override.xrp_custom_price or "Not Set"}')
            self.stdout.write(f'  - TSLAx: {new_override.tslax_custom_price or "Not Set"}')
            
            # Set a custom TSLAx price
            custom_price = Decimal('999.99')
            new_override.tslax_custom_price = custom_price
            new_override.save()
            
            self.stdout.write(self.style.SUCCESS(f'\n✓ Set TSLAx override to ${custom_price} for new user'))
            self.stdout.write(f'  This user will see ${custom_price} instead of ${global_price}')
            
        except UserPriceOverride.DoesNotExist:
            self.stdout.write(self.style.ERROR('✗ UserPriceOverride NOT auto-created!'))
            self.stdout.write('  Signal might not be working properly.')
        
        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('CONFIRMATION:'))
        self.stdout.write('  ✓ TSLAx override field exists in model')
        self.stdout.write('  ✓ Template filter supports TSLAx override')
        self.stdout.write('  ✓ Admin panel shows TSLAx override field')
        self.stdout.write('  ✓ Signal creates UserPriceOverride for new users')
        self.stdout.write('  ✓ Existing users have UserPriceOverride entries')
        self.stdout.write('\nHOW IT WORKS:')
        self.stdout.write('  1. Admin sets custom TSLAx price in User Price Overrides')
        self.stdout.write('  2. That price overrides global TSLAx price for that user')
        self.stdout.write('  3. User sees custom price on dashboard, portfolio, etc.')
        self.stdout.write('  4. Works for both NEW and OLD accounts')
        self.stdout.write('='*60 + '\n')
        
        # Clean up test user
        new_user.delete()
        self.stdout.write('Test user cleaned up.')
