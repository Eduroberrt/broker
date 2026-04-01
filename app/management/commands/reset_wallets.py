from django.core.management.base import BaseCommand
from app.models import UserWallet

class Command(BaseCommand):
    help = 'Reset all user wallet balances to 0'

    def handle(self, *args, **options):
        count = UserWallet.objects.all().update(balance=0)
        self.stdout.write(self.style.SUCCESS(f'Successfully reset {count} wallet balances to $0.00'))
