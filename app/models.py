from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User

class CryptoAsset(models.Model):
    """Model to store cryptocurrency prices controlled by admin"""
    name = models.CharField(max_length=50, unique=True, help_text="Full name (e.g., Bitcoin)")
    symbol = models.CharField(max_length=10, unique=True, help_text="Symbol (e.g., BTC)")
    icon = models.CharField(max_length=10, default="₿", help_text="Icon character to display")
    color = models.CharField(max_length=20, default="#f7931a", help_text="Hex color code")
    
    # Price information
    current_price = models.DecimalField(
        max_digits=20, 
        decimal_places=8, 
        validators=[MinValueValidator(0)],
        help_text="Current market price in USD"
    )
    base_price = models.DecimalField(
        max_digits=20, 
        decimal_places=8, 
        validators=[MinValueValidator(0)],
        help_text="Base price for calculating percentage change"
    )
    
    # Display order
    order = models.IntegerField(default=0, help_text="Display order (lower numbers appear first)")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Crypto Asset"
        verbose_name_plural = "Crypto Assets"
    
    def __str__(self):
        return f"{self.name} ({self.symbol})"
    
    @property
    def percentage_change(self):
        """Calculate percentage change from base price"""
        if self.base_price == 0:
            return 0
        change = ((self.current_price - self.base_price) / self.base_price) * 100
        return round(float(change), 2)
    
    @property
    def is_positive_change(self):
        """Check if price change is positive"""
        return self.percentage_change >= 0
    
    @property
    def formatted_price(self):
        """Format price based on value"""
        price = float(self.current_price)
        if price < 1:
            return f"${price:.4f}"
        elif price < 100:
            return f"${price:.2f}"
        else:
            return f"${price:,.2f}"
    
    @property
    def chart_data(self):
        """Generate chart data based on current vs base price"""
        change_percent = self.percentage_change
        # Generate 12 data points showing trend
        data_points = []
        for i in range(12):
            # Gradual change from base to current
            progress = i / 11  # 0 to 1
            point_change = change_percent * progress
            data_points.append(round(point_change, 2))
        return data_points


class ReceiveTransaction(models.Model):
    """Model to store receive transaction submissions"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='receive_transactions')
    crypto_asset = models.ForeignKey(CryptoAsset, on_delete=models.CASCADE, related_name='receive_transactions')
    wallet_address = models.CharField(max_length=255, help_text="Wallet address used for receiving")
    proof_of_transfer = models.FileField(upload_to='proof_transfers/', help_text="Upload proof of transfer file")
    
    # Admin fills these
    amount = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Amount in USD (filled by admin)"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, help_text="Admin notes about this transaction")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Receive Transaction"
        verbose_name_plural = "Receive Transactions"
    
    def __str__(self):
        return f"{self.user.username} - {self.crypto_asset.symbol} - {self.status}"


class UserWallet(models.Model):
    """Model to store user's cryptocurrency wallet balances in USD"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wallets')
    crypto_asset = models.ForeignKey(CryptoAsset, on_delete=models.CASCADE, related_name='user_wallets')
    balance = models.DecimalField(
        max_digits=20, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0)],
        help_text="User's balance in USD for this cryptocurrency"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'crypto_asset']
        ordering = ['crypto_asset__order']
        verbose_name = "User Wallet"
        verbose_name_plural = "User Wallets"
    
    def __str__(self):
        return f"{self.user.username} - {self.crypto_asset.symbol}: {self.balance}"


class SwapTransaction(models.Model):
    """Model to store swap transactions between cryptocurrencies"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='swap_transactions')
    from_crypto = models.ForeignKey(CryptoAsset, on_delete=models.CASCADE, related_name='swaps_from')
    to_crypto = models.ForeignKey(CryptoAsset, on_delete=models.CASCADE, related_name='swaps_to')
    from_amount_usd = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Amount swapped FROM in USD"
    )
    to_amount_usd = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Amount received TO in USD"
    )
    from_price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Price of FROM crypto at swap time"
    )
    to_price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Price of TO crypto at swap time"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Swap Transaction"
        verbose_name_plural = "Swap Transactions"
    
    def __str__(self):
        return f"{self.user.username} - {self.from_crypto.symbol} to {self.to_crypto.symbol} - ${self.from_amount_usd}"


class SellTransaction(models.Model):
    """Model to store sell transaction submissions"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sell_transactions')
    crypto_asset = models.ForeignKey(CryptoAsset, on_delete=models.CASCADE, related_name='sell_transactions')
    amount_to_sell = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Amount user wants to sell in USD"
    )
    proof_of_transfer = models.FileField(upload_to='sell_proofs/', help_text="Upload proof of crypto sent")
    
    # Admin fills these
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Amount paid to user in USD (filled by admin)"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, help_text="Admin notes about this transaction")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Sell Transaction"
        verbose_name_plural = "Sell Transactions"
    
    def __str__(self):
        return f"{self.user.username} - Sell {self.crypto_asset.symbol} - ${self.amount_to_sell} - {self.status}"


class Notification(models.Model):
    """Model for user notifications created by admin"""
    title = models.CharField(max_length=200, help_text="Notification title")
    message = models.TextField(help_text="Notification message")
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, help_text="Specific user (leave blank for all users)")
    is_read = models.BooleanField(default=False, help_text="Whether notification has been read")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
    
    def __str__(self):
        if self.user:
            return f"{self.title} - {self.user.username}"
        return f"{self.title} - All Users"
