from django.contrib import admin
from django.utils.html import format_html
from .models import CryptoAsset, ReceiveTransaction, UserWallet, SellTransaction, Notification, UserProfile, UserHolding, ContactMessage

@admin.register(CryptoAsset)
class CryptoAssetAdmin(admin.ModelAdmin):
    list_display = ['name', 'symbol', 'asset_type', 'formatted_price', 'base_price', 'percentage_change', 'is_in_watchlist', 'order', 'updated_at']
    list_editable = ['order', 'is_in_watchlist']
    list_filter = ['asset_type', 'is_in_watchlist']
    search_fields = ['name', 'symbol']
    ordering = ['order', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'symbol', 'icon', 'icon_url', 'color', 'asset_type', 'is_in_watchlist', 'order')
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


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_transactions', 'email_security', 'two_factor_enabled', 'updated_at']
    list_filter = ['email_transactions', 'email_security', 'email_marketing', 'two_factor_enabled', 'created_at']
    search_fields = ['user__username', 'user__email', 'bio']
    ordering = ['-updated_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'bio', 'profile_image')
        }),
        ('Notification Preferences', {
            'fields': ('email_transactions', 'email_security', 'email_marketing')
        }),
        ('Security Settings', {
            'fields': ('two_factor_enabled',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']


@admin.register(UserHolding)
class UserHoldingAdmin(admin.ModelAdmin):
    list_display = ['user', 'crypto_asset', 'balance', 'average_buy_price', 'current_value_display', 'profit_loss_display', 'updated_at']
    list_filter = ['crypto_asset', 'created_at']
    search_fields = ['user__username', 'crypto_asset__name', 'crypto_asset__symbol']
    ordering = ['-balance']
    
    fieldsets = (
        ('Holding Information', {
            'fields': ('user', 'crypto_asset', 'balance', 'average_buy_price')
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def current_value_display(self, obj):
        value = float(obj.current_value)
        formatted_value = '${:,.2f}'.format(value)
        return format_html('<span style="font-weight: bold;">{}</span>', formatted_value)
    current_value_display.short_description = 'Current Value'
    
    def profit_loss_display(self, obj):
        pl = float(obj.profit_loss)
        pl_pct = float(obj.profit_loss_percentage)
        color = 'green' if pl >= 0 else 'red'
        symbol = '▲' if pl >= 0 else '▼'
        formatted_pl = '${:,.2f}'.format(abs(pl))
        formatted_pct = '{:+.2f}%'.format(pl_pct)
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {} ({})</span>',
            color, symbol, formatted_pl, formatted_pct
        )
    profit_loss_display.short_description = 'P/L'


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'status', 'created_at', 'has_response']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'email', 'subject', 'message']
    list_editable = ['status']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Message Information', {
            'fields': ('user', 'name', 'email', 'subject', 'message', 'status')
        }),
        ('Admin Response', {
            'fields': ('admin_response', 'responded_at'),
            'description': 'Add your response to the user message'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def has_response(self, obj):
        if obj.admin_response:
            return format_html('<span style="color: green; font-weight: bold;">✓ Yes</span>')
        return format_html('<span style="color: orange;">✗ No</span>')
    has_response.short_description = 'Responded'
