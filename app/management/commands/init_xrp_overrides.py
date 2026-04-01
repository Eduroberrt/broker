from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from app.models import UserPriceOverride

class Command(BaseCommand):
    help = 'Create UserPriceOverride entries for all users'

    def handle(self, *args, **options):
        users = User.objects.all()
        
        if not users.exists():
            self.stdout.write(self.style.WARNING('No users found in database'))
            return
        
        created_count = 0
        existing_count = 0
        
        self.stdout.write(f'\n🔄 Creating XRP price override entries for {users.count()} users...\n')
        
        for user in users:
            override, created = UserPriceOverride.objects.get_or_create(
                user=user,
                defaults={'xrp_custom_price': None}
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created: {user.username} (using global XRP price)')
                )
            else:
                existing_count += 1
                if override.xrp_custom_price:
                    self.stdout.write(f'  Existing: {user.username} (custom: ${override.xrp_custom_price})')
                else:
                    self.stdout.write(f'  Existing: {user.username} (using global)')
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ Summary:')
        )
        self.stdout.write(f'   • Created: {created_count} new entries')
        self.stdout.write(f'   • Existing: {existing_count} entries')
        self.stdout.write(f'   • Total: {created_count + existing_count} users')
        self.stdout.write('\nAdmin can now set custom XRP prices per user in "User XRP Price Overrides" section.')
