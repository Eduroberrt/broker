from django.contrib import admin
from django.utils.html import format_html
from django.shortcuts import render, redirect
from django import forms
from decimal import Decimal
from .models import CryptoAsset, ReceiveTransaction, UserWallet, SellTransaction, Notification, UserProfile, UserHolding, ContactMessage, UserPriceOverride

@admin.register(CryptoAsset)
class CryptoAssetAdmin(admin.ModelAdmin):
    list_display = ['name', 'symbol', 'asset_type', 'formatted_price', 'base_price', 'percentage_change', 'is_in_watchlist', 'order', 'updated_at', 'api_status']
    list_editable = ['order', 'is_in_watchlist']
    list_filter = ['asset_type', 'is_in_watchlist']
    search_fields = ['name', 'symbol']
    ordering = ['order', 'name']
    
    def get_fieldsets(self, request, obj=None):
        # Allow editing XRP and TSLAx prices manually
        if obj and obj.symbol in ['XRP', 'TSLAx']:
            return (
                ('Basic Information', {
                    'fields': ('name', 'symbol', 'icon', 'icon_url', 'color', 'asset_type', 'is_in_watchlist', 'order')
                }),
                (f'Price Information (Manual Control for {obj.symbol})', {
                    'fields': ('current_price', 'base_price'),
                    'description': f'{obj.symbol} prices are manually controlled. Update current_price to change market price.'
                }),
            )
        else:
            return (
                ('Basic Information', {
                    'fields': ('name', 'symbol', 'icon', 'icon_url', 'color', 'asset_type', 'is_in_watchlist', 'order')
                }),
                ('Price Information (Auto-Updated from API)', {
                    'fields': ('current_price', 'base_price'),
                    'description': 'Prices are automatically updated from CoinGecko API. Manual editing is disabled for non-XRP and non-TSLAx assets.'
                }),
            )
    
    def get_readonly_fields(self, request, obj=None):
        # Make price fields readonly for all assets except XRP and TSLAx
        if obj and obj.symbol not in ['XRP', 'TSLAx']:
            return ['current_price', 'base_price']
        return []
    
    def get_queryset(self, request):
        # Show XRP and TSLAx in admin list view
        qs = super().get_queryset(request)
        return qs.filter(symbol__in=['XRP', 'TSLAx'])
    
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
    
    def api_status(self, obj):
        if obj.symbol in ['XRP', 'TSLAx']:
            return format_html('<span style="color: orange; font-weight: bold;">⚙️ Manual</span>')
        else:
            return format_html('<span style="color: green; font-weight: bold;">🔄 Auto API</span>')
    api_status.short_description = 'Price Source'


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
            from app.models import UserProfile
            # 1) Add to specific crypto's wallet balance
            wallet, created = UserWallet.objects.get_or_create(
                user=obj.user,
                crypto_asset=obj.crypto_asset
            )
            wallet.balance += obj.amount
            wallet.save()
            
            # 2) Recalculate wallet_balance from sum of all coin balances
            profile, created = UserProfile.objects.get_or_create(user=obj.user)
            coin_sum = sum(w.balance for w in obj.user.wallets.all())
            profile.wallet_balance = coin_sum
            profile.save()
        
        super().save_model(request, obj, form, change)

@admin.register(UserPriceOverride)
class UserPriceOverrideAdmin(admin.ModelAdmin):
    list_display = ['user', 'xrp_custom_price_display', 'tslax_custom_price_display', 'status_display', 'updated_at']
    search_fields = ['user__username']
    ordering = ['user__username']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Price Overrides', {
            'fields': ('xrp_custom_price', 'tslax_custom_price'),
            'description': 'Set custom prices for this user. Leave blank to use global prices. These prices will show site-wide for this user only.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def xrp_custom_price_display(self, obj):
        if obj.xrp_custom_price:
            formatted_price = '${:,.8f}'.format(float(obj.xrp_custom_price))
            return format_html('<span style="font-weight: bold; color: #bd24df;">{}</span>', formatted_price)
        return format_html('<span style="color: gray;">Not Set</span>')
    xrp_custom_price_display.short_description = 'Custom XRP Price'
    
    def tslax_custom_price_display(self, obj):
        if obj.tslax_custom_price:
            formatted_price = '${:,.2f}'.format(float(obj.tslax_custom_price))
            return format_html('<span style="font-weight: bold; color: #bd24df;">{}</span>', formatted_price)
        return format_html('<span style="color: gray;">Not Set</span>')
    tslax_custom_price_display.short_description = 'Custom TSLAx Price'
    
    def status_display(self, obj):
        statuses = []
        if obj.xrp_custom_price:
            statuses.append('XRP')
        if obj.tslax_custom_price:
            statuses.append('TSLAx')
        if statuses:
            return format_html('<span style="color: green; font-weight: bold;">✓ {}</span>', ', '.join(statuses))
        return format_html('<span style="color: gray;">○ Using Global</span>')
    status_display.short_description = 'Status'


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
            from app.models import UserProfile
            # 1) Deduct from specific crypto's wallet balance
            wallet = UserWallet.objects.filter(user=obj.user, crypto_asset=obj.crypto_asset).first()
            
            if wallet and wallet.balance >= obj.amount_to_sell:
                wallet.balance -= obj.amount_to_sell
                wallet.save()
            
            # 2) Recalculate wallet_balance from sum of all coin balances
            profile, created = UserProfile.objects.get_or_create(user=obj.user)
            coin_sum = sum(w.balance for w in obj.user.wallets.all())
            profile.wallet_balance = coin_sum
            profile.save()
        
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
    list_display = ['username', 'wallet_balance_display', 'coin_balances_sum', 'updated_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'user__email']
    ordering = ['-updated_at']
    
    def username(self, obj):
        return obj.user.username
    username.short_description = 'User'
    username.admin_order_field = 'user__username'
    
    def wallet_balance_display(self, obj):
        return f'${obj.wallet_balance:,.2f}'
    wallet_balance_display.short_description = 'Wallet Balance (USD)'
    wallet_balance_display.admin_order_field = 'wallet_balance'
    
    def coin_balances_sum(self, obj):
        """Calculate sum of all coin balances"""
        total = sum(wallet.balance for wallet in obj.user.wallets.all())
        return f'${total:,.2f}'
    coin_balances_sum.short_description = 'Sum of Coin Balances'
    
    def get_form(self, request, obj=None, **kwargs):
        """Add dynamic fields for coin balances"""
        # Temporarily disable field validation for dynamic fields
        kwargs['fields'] = None
        form = super().get_form(request, obj, **kwargs)
        
        if obj:
            # Get all user's wallets
            wallets = obj.user.wallets.select_related('crypto_asset').order_by('crypto_asset__order')
            
            # Create fields for each wallet
            for wallet in wallets:
                field_name = f'coin_balance_{wallet.crypto_asset.symbol}'
                form.base_fields[field_name] = forms.DecimalField(
                    label=f'{wallet.crypto_asset.name} ({wallet.crypto_asset.symbol})',
                    initial=wallet.balance,
                    max_digits=20,
                    decimal_places=2,
                    min_value=Decimal('0'),
                    required=False,
                    help_text='Balance in USD'
                )
        
        return form
    
    def get_fields(self, request, obj=None):
        """Return all fields including dynamic ones"""
        fields = ['user', 'wallet_balance']
        
        if obj:
            # Add dynamic coin balance fields
            wallets = obj.user.wallets.select_related('crypto_asset').order_by('crypto_asset__order')
            for wallet in wallets:
                fields.append(f'coin_balance_{wallet.crypto_asset.symbol}')
        
        return fields
    
    def get_fieldsets(self, request, obj=None):
        """Dynamically build fieldsets with coin balance fields"""
        fieldsets = [
            ('User Information', {
                'fields': ('user',)
            }),
            ('Wallet Balance', {
                'fields': ('wallet_balance',),
                'description': 'Main wallet balance shown in user dashboard (auto-calculated from coin balances below)'
            }),
        ]
        
        if obj:
            # Get all coin balance fields
            wallets = obj.user.wallets.select_related('crypto_asset').order_by('crypto_asset__order')
            coin_fields = [f'coin_balance_{w.crypto_asset.symbol}' for w in wallets]
            
            if coin_fields:
                fieldsets.append(
                    ('Individual Coin Balances', {
                        'fields': tuple(coin_fields),
                        'description': 'Edit individual cryptocurrency balances. Wallet balance will auto-update to match the sum.'
                    })
                )
        
        return fieldsets
    
    readonly_fields = ['created_at', 'updated_at', 'user']
    
    def save_model(self, request, obj, form, change):
        """Update coin balances and recalculate wallet_balance"""
        # First save the profile
        super().save_model(request, obj, form, change)
        
        if obj:
            # Update individual coin balances from form data
            wallets = obj.user.wallets.select_related('crypto_asset').order_by('crypto_asset__order')
            
            for wallet in wallets:
                field_name = f'coin_balance_{wallet.crypto_asset.symbol}'
                if field_name in form.cleaned_data:
                    new_balance = form.cleaned_data[field_name]
                    if new_balance is not None and wallet.balance != new_balance:
                        wallet.balance = new_balance
                        wallet.save()
            
            # Recalculate wallet_balance from sum of all coin balances
            coin_sum = sum(w.balance for w in obj.user.wallets.all())
            if obj.wallet_balance != coin_sum:
                obj.wallet_balance = coin_sum
                obj.save()
                
                from django.contrib import messages
                messages.success(
                    request,
                    f'Wallet balance automatically updated to ${coin_sum:,.2f} (sum of all coin balances)'
                )



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
