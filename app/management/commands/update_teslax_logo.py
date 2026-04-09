from django.core.management.base import BaseCommand
from app.models import CryptoAsset

class Command(BaseCommand):
    help = 'Update TSLAx to use teslax.jpeg logo'

    def handle(self, *args, **options):
        try:
            tesla = CryptoAsset.objects.get(symbol='TSLAx')
            tesla.icon_url = '/static/images/teslax.jpeg'
            tesla.save()
            self.stdout.write(self.style.SUCCESS(f'✓ TSLAx icon_url updated to: {tesla.icon_url}'))
        except CryptoAsset.DoesNotExist:
            self.stdout.write(self.style.ERROR('✗ TSLAx not found in database'))
