from django.contrib import admin
from django.utils.html import format_html
from django.shortcuts import render, redirect
from django import forms
from .models import CryptoAsset, ReceiveTransaction, UserWallet, SellTransaction, Notification, UserProfile, UserHolding, ContactMessage, UserPriceOverride

@admin.register(CryptoAsset)
class CryptoAssetAdmin(admin.ModelAdmin):
    list_display = ['name', 'symbol', 'asset_type', 'formatted_price', 'base_price', 'percentage_change', 'is_in_watchlist', 'order', 'updated_at', 'api_status']
    list_editable = ['order', 'is_in_watchlist']
    list_filter = ['asset_type', 'is_in_watchlist']
    search_fields = ['name', 'symbol']
    ordering = ['order', 'name']
    
    def get_fieldsets(self, request, obj=None):
        # Only allow editing XRP prices manually
        if obj and obj.symbol == 'XRP':
            return (
                ('Basic Information', {
                    'fields': ('name', 'symbol', 'icon', 'icon_url', 'color', 'asset_type', 'is_in_watchlist', 'order')
                }),
                ('Price Information (Manual Control for XRP)', {
                    'fields': ('current_price', 'base_price'),
                    'description': 'XRP prices are manually controlled. Update current_price to change market price.'
                }),
            )
        else:
            return (
                ('Basic Information', {
                    'fields': ('name', 'symbol', 'icon', 'icon_url', 'color', 'asset_type', 'is_in_watchlist', 'order')
                }),
                ('Price Information (Auto-Updated from API)', {
                    'fields': ('current_price', 'base_price'),
                    'description': 'Prices are automatically updated from CoinGecko API. Manual editing is disabled for non-XRP assets.'
                }),
            )
    
    def get_readonly_fields(self, request, obj=None):
        # Make price fields readonly for all assets except XRP
        if obj and obj.symbol != 'XRP':
            return ['current_price', 'base_price']
        return []
    
    def get_queryset(self, request):
        # Only show XRP in admin list view
        qs = super().get_queryset(request)
        return qs.filter(symbol='XRP')
    
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
        if obj.symbol == 'XRP':
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
            
            # 2) Add to user's main wallet balance
            profile, created = UserProfile.objects.get_or_create(user=obj.user)
            profile.wallet_balance += obj.amount
            profile.save()
        
        super().save_model(request, obj, form, change)

@admin.register(UserWallet)
class UserWalletAdmin(admin.ModelAdmin):
    list_display = ['username', 'wallet_balance_display']
    search_fields = ['user__username']
    actions = None
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def get_queryset(self, request):
        # Get all UserProfile objects (one per user)
        from app.models import UserProfile
        # We'll use UserProfile as the base, but need to adapt for UserWallet registration
        # Actually, let's filter UserWallet to show one per user (any crypto, doesn't matter)
        qs = super().get_queryset(request)
        # Get one wallet per user (using distinct on user)
        seen_users = set()
        filtered_qs = []
        for wallet in qs.select_related('user', 'user__profile'):
            if wallet.user.id not in seen_users:
                seen_users.add(wallet.user.id)
                filtered_qs.append(wallet.id)
        return qs.filter(id__in=filtered_qs)
    
    def username(self, obj):
        return obj.user.username
    username.short_description = 'User'
    username.admin_order_field = 'user__username'
    
    def wallet_balance_display(self, obj):
        """Display user's wallet balance from UserProfile"""
        from app.models import UserProfile
        if hasattr(obj.user, 'profile'):
            profile = obj.user.profile
        else:
            profile, created = UserProfile.objects.get_or_create(user=obj.user)
        return f'${profile.wallet_balance:,.2f}'
    wallet_balance_display.short_description = 'Wallet Balance (USD)'
    
    # Form configuration
    fields = ['user', 'wallet_balance']
    readonly_fields = ['user']
    
    def get_form(self, request, obj=None, **kwargs):
        from django import forms
        from app.models import UserProfile
        
        class UserWalletBalanceForm(forms.ModelForm):
            wallet_balance = forms.DecimalField(
                max_digits=20,
                decimal_places=2,
                label='Wallet Balance (USD)',
                widget=forms.NumberInput(attrs={'step': '0.01'}),
                help_text='Enter the new wallet balance for this user'
            )
            
            class Meta:
                model = UserWallet
                fields = ['user', 'wallet_balance']
            
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                if self.instance and self.instance.pk and self.instance.user:
                    profile, created = UserProfile.objects.get_or_create(user=self.instance.user)
                    self.fields['wallet_balance'].initial = profile.wallet_balance
                if 'user' in self.fields:
                    self.fields['user'].disabled = True
        
        kwargs['form'] = UserWalletBalanceForm
        return super().get_form(request, obj, **kwargs)
    
    def save_model(self, request, obj, form, change):
        """Save the wallet balance to UserProfile"""
        if change and 'wallet_balance' in form.cleaned_data:
            from app.models import UserProfile
            new_balance = form.cleaned_data['wallet_balance']
            profile, created = UserProfile.objects.get_or_create(user=obj.user)
            profile.wallet_balance = new_balance
            profile.save()
            self.message_user(request, f"Wallet balance for {obj.user.username} set to ${new_balance:,.2f}")
        # Don't save the UserWallet object itself
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['title'] = 'User Wallet Balances'
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(UserPriceOverride)
class UserPriceOverrideAdmin(admin.ModelAdmin):
    list_display = ['user', 'xrp_custom_price_display', 'status_display', 'updated_at']
    search_fields = ['user__username']
    ordering = ['user__username']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('XRP Price Override', {
            'fields': ('xrp_custom_price',),
            'description': 'Set a custom XRP price for this user. Leave blank to use global XRP price. This price will show site-wide for this user only.'
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
    
    def status_display(self, obj):
        if obj.xrp_custom_price:
            return format_html('<span style="color: green; font-weight: bold;">✓ Active</span>')
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
            
            # 2) Deduct from user's main wallet balance (independent of crypto balance check)
            profile, created = UserProfile.objects.get_or_create(user=obj.user)
            if profile.wallet_balance >= obj.amount_to_sell:
                profile.wallet_balance -= obj.amount_to_sell
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
