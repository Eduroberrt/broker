from django.contrib import admin
from django.utils.html import format_html
from .models import CryptoAsset, ReceiveTransaction, UserWallet, SellTransaction, Notification

@admin.register(CryptoAsset)
class CryptoAssetAdmin(admin.ModelAdmin):
    list_display = ['name', 'symbol', 'formatted_price', 'base_price', 'percentage_change', 'order', 'updated_at']
    list_editable = ['order']
    search_fields = ['name', 'symbol']
    ordering = ['order', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'symbol', 'icon', 'color', 'order')
        }),
        ('Price Information', {
            'fields': ('current_price', 'base_price'),
            'description': 'Update current_price to change market price. Base price is used to calculate percentage change.'
        }),
    )
    
    readonly_fields = []
    
    def percentage_change(self, obj):
        change = obj.percentage_change
        color = 'green' if change >= 0 else 'red'
        symbol = '▲' if change >= 0 else '▼'
        # Format the number first, then pass to format_html
        formatted_change = f'{float(change):+.2f}'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}%</span>', 
            color, 
            symbol, 
            formatted_change
        )
    percentage_change.short_description = 'Change %'


@admin.register(ReceiveTransaction)
class ReceiveTransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'crypto_asset', 'wallet_address', 'amount', 'status', 'created_at', 'updated_at']
    list_filter = ['status', 'crypto_asset', 'created_at']
    search_fields = ['user__username', 'wallet_address']
    list_editable = ['amount', 'status']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Transaction Information', {
            'fields': ('user', 'crypto_asset', 'wallet_address', 'proof_of_transfer')
        }),
        ('Admin Section', {
            'fields': ('amount', 'status', 'admin_notes'),
            'description': 'Fill in the amount and change status to confirm the transaction. This will update user wallet balance.'
        }),
    )
    
    readonly_fields = ['user', 'crypto_asset', 'wallet_address', 'proof_of_transfer']
    
    def save_model(self, request, obj, form, change):
        """When status changes to confirmed, update user wallet with USD amount"""
        if change and 'status' in form.changed_data and obj.status == 'confirmed' and obj.amount:
            # Get or create user wallet for this crypto
            wallet, created = UserWallet.objects.get_or_create(
                user=obj.user,
                crypto_asset=obj.crypto_asset
            )
            # Add the USD amount directly to wallet balance
            wallet.balance += obj.amount
            wallet.save()
        
        super().save_model(request, obj, form, change)


@admin.register(UserWallet)
class UserWalletAdmin(admin.ModelAdmin):
    list_display = ['user', 'crypto_asset', 'balance', 'updated_at']
    list_filter = ['crypto_asset']
    search_fields = ['user__username']
    ordering = ['user', 'crypto_asset__order']
    
    readonly_fields = ['created_at', 'updated_at']


@admin.register(SellTransaction)
class SellTransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'crypto_asset', 'amount_to_sell', 'status', 'created_at', 'updated_at']
    list_filter = ['status', 'crypto_asset', 'created_at']
    search_fields = ['user__username']
    list_editable = ['status']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Transaction Information', {
            'fields': ('user', 'crypto_asset', 'amount_to_sell', 'proof_of_transfer', 'status')
        }),
    )
    
    readonly_fields = ['user', 'crypto_asset', 'amount_to_sell', 'proof_of_transfer']
    
    def save_model(self, request, obj, form, change):
        """When status changes to confirmed, deduct from user wallet"""
        if change and 'status' in form.changed_data and obj.status == 'confirmed':
            # Get user wallet for this crypto
            wallet = UserWallet.objects.filter(user=obj.user, crypto_asset=obj.crypto_asset).first()
            
            if wallet and wallet.balance >= obj.amount_to_sell:
                # Deduct the amount from wallet balance
                wallet.balance -= obj.amount_to_sell
                wallet.save()
        
        super().save_model(request, obj, form, change)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user_display', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['title', 'message', 'user__username']
    list_editable = ['is_read']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Notification Details', {
            'fields': ('title', 'message', 'user'),
            'description': 'Leave user blank to send notification to all users.'
        }),
        ('Status', {
            'fields': ('is_read',)
        }),
    )
    
    def user_display(self, obj):
        return obj.user.username if obj.user else "All Users"
    user_display.short_description = 'Recipient'
