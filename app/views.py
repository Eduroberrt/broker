from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.contrib.auth.models import User
from datetime import datetime
from django.http import JsonResponse
from .models import CryptoAsset, ReceiveTransaction, UserWallet, SwapTransaction, SellTransaction, Notification, UserProfile
from PIL import Image
from decimal import Decimal
import os


def home(request):
    """Home page view"""
    crypto_assets = CryptoAsset.objects.all().order_by('order')
    context = {
        'current_year': datetime.now().year,
        'crypto_assets': crypto_assets,
    }
    return render(request, 'home.html', context)


def documentation(request):
    """Documentation page view"""
    context = {
        'current_year': datetime.now().year
    }
    return render(request, 'documentation.html', context)


def signin_view(request):
    """Sign in view"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # Try to get user by email
        try:
            user = User.objects.get(email=email)
            user = authenticate(request, username=user.username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, 'Successfully logged in!')
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid email or password.')
        except User.DoesNotExist:
            messages.error(request, 'Invalid email or password.')
    
    context = {
        'current_year': datetime.now().year
    }
    return render(request, 'auth/signin.html', context)


def signup_view(request):
    """Sign up view"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Validation
        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
        else:
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1
            )
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('dashboard')
    
    context = {
        'current_year': datetime.now().year
    }
    return render(request, 'auth/signup.html', context)


@login_required
def dashboard(request):
    """Dashboard view - requires authentication"""
    # Get all crypto assets from database
    all_assets = CryptoAsset.objects.all()
    
    # Separate assets by type
    watchlist_assets = all_assets.filter(is_in_watchlist=True)
    crypto_assets = all_assets.filter(asset_type='crypto')
    stock_assets = all_assets.filter(asset_type='stock')
    
    # Get user's wallet balances
    user_wallets = UserWallet.objects.filter(user=request.user).select_related('crypto_asset')
    
    # Create a dictionary for quick wallet lookup by crypto_asset id
    wallet_dict = {wallet.crypto_asset.id: wallet.balance for wallet in user_wallets}
    
    # Get wallet balance from UserProfile (what admin manages)
    total_balance = request.user.profile.wallet_balance if hasattr(request.user, 'profile') else Decimal('0')
    
    # Calculate total gain/loss
    total_base_value = Decimal('0')
    for wallet in user_wallets:
        if wallet.balance > 0:
            asset = wallet.crypto_asset
            crypto_amount = wallet.balance / asset.current_price if asset.current_price > 0 else Decimal('0')
            total_base_value += crypto_amount * asset.base_price
    
    total_gain = float(total_balance - total_base_value)
    total_gain_percentage = (total_gain / float(total_base_value) * 100) if total_base_value > 0 else 0
    is_total_profit = total_gain >= 0
    
    context = {
        'current_year': datetime.now().year,
        'watchlist_assets': watchlist_assets,
        'crypto_assets': crypto_assets,
        'stock_assets': stock_assets,
        'wallet_dict': wallet_dict,
        'total_balance': total_balance,
        'total_gain': total_gain,
        'total_gain_percentage': total_gain_percentage,
        'is_total_profit': is_total_profit,
    }
    return render(request, 'dashboard.html', context)


@login_required
def send_view(request):
    """Send crypto view"""
    crypto_assets = CryptoAsset.objects.all()
    context = {
        'current_year': datetime.now().year,
        'crypto_assets': crypto_assets
    }
    return render(request, 'send.html', context)


@login_required
def receive_view(request):
    """Receive crypto view"""
    crypto_assets = CryptoAsset.objects.all()
    
    if request.method == 'POST':
        crypto_symbol = request.POST.get('crypto_asset')
        wallet_address = request.POST.get('wallet_address')
        proof_file = request.FILES.get('proof_of_transfer')
        
        if crypto_symbol and wallet_address and proof_file:
            try:
                crypto_asset = CryptoAsset.objects.get(symbol=crypto_symbol)
                
                transaction = ReceiveTransaction.objects.create(
                    user=request.user,
                    crypto_asset=crypto_asset,
                    wallet_address=wallet_address,
                    proof_of_transfer=proof_file,
                    status='pending'
                )
                messages.success(request, 'Your transaction has been submitted successfully! Please wait for admin confirmation.')
                return redirect('receive')
            except CryptoAsset.DoesNotExist:
                messages.error(request, 'Invalid cryptocurrency selected.')
        else:
            messages.error(request, 'Please fill all fields and upload proof of transfer.')
    
    # Get user's transaction history
    transactions = ReceiveTransaction.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'current_year': datetime.now().year,
        'crypto_assets': crypto_assets,
        'transactions': transactions
    }
    return render(request, 'receive.html', context)


@login_required
def swap_view(request):
    """Swap crypto view"""
    from decimal import Decimal
    
    crypto_assets = CryptoAsset.objects.all()
    
    if request.method == 'POST':
        from_symbol = request.POST.get('from_crypto')
        to_symbol = request.POST.get('to_crypto')
        from_amount_usd = request.POST.get('from_amount_usd')
        
        try:
            from_crypto = CryptoAsset.objects.get(symbol=from_symbol)
            to_crypto = CryptoAsset.objects.get(symbol=to_symbol)
            from_amount_usd = Decimal(from_amount_usd)
            
            from_wallet = UserWallet.objects.filter(user=request.user, crypto_asset=from_crypto).first()
            
            if not from_wallet or from_wallet.balance < from_amount_usd:
                return JsonResponse({'success': False, 'message': 'Insufficient balance'})
            
            to_amount_usd = from_amount_usd
            
            from_wallet.balance -= from_amount_usd
            from_wallet.save()
            
            to_wallet, created = UserWallet.objects.get_or_create(
                user=request.user,
                crypto_asset=to_crypto
            )
            to_wallet.balance += to_amount_usd
            to_wallet.save()
            
            # Record swap transaction
            SwapTransaction.objects.create(
                user=request.user,
                from_crypto=from_crypto,
                to_crypto=to_crypto,
                from_amount_usd=from_amount_usd,
                to_amount_usd=to_amount_usd,
                from_price=from_crypto.current_price,
                to_price=to_crypto.current_price
            )
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    # Get user wallets
    user_wallets = UserWallet.objects.filter(user=request.user).select_related('crypto_asset')
    wallet_dict = {wallet.crypto_asset.symbol: float(wallet.balance) for wallet in user_wallets}
    
    import json
    context = {
        'current_year': datetime.now().year,
        'crypto_assets': crypto_assets,
        'wallet_dict_json': json.dumps(wallet_dict)
    }
    return render(request, 'swap.html', context)


@login_required
def buy_view(request):
    """Buy crypto view"""
    crypto_assets = CryptoAsset.objects.all()
    context = {
        'current_year': datetime.now().year,
        'crypto_assets': crypto_assets
    }
    return render(request, 'buy.html', context)


@login_required
def sell_view(request):
    """Sell crypto view"""
    # Only show coins with wallet addresses (the 4 watchlist coins)
    crypto_assets = CryptoAsset.objects.filter(is_in_watchlist=True, receive_wallet_address__isnull=False).exclude(receive_wallet_address='')
    
    if request.method == 'POST':
        crypto_symbol = request.POST.get('crypto_asset')
        amount_to_sell = request.POST.get('amount_to_sell')
        proof_file = request.FILES.get('proof_of_transfer')
        
        if crypto_symbol and amount_to_sell and proof_file:
            try:
                crypto_asset = CryptoAsset.objects.get(symbol=crypto_symbol)
                
                # Create sell transaction
                transaction = SellTransaction.objects.create(
                    user=request.user,
                    crypto_asset=crypto_asset,
                    amount_to_sell=amount_to_sell,
                    proof_of_transfer=proof_file
                )
                
                return redirect('sell')
            except Exception as e:
                messages.error(request, f'Error creating transaction: {str(e)}')
    
    # Get transaction history
    transactions = SellTransaction.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'current_year': datetime.now().year,
        'crypto_assets': crypto_assets,
        'transactions': transactions
    }
    return render(request, 'sell.html', context)


@login_required
def logout_view(request):
    """Logout view"""
    logout(request)
    messages.success(request, 'Successfully logged out!')
    return redirect('home')


@login_required
def notifications_view(request):
    """View and manage notifications"""
    from django.db import models
    # Get notifications for this user (specific to user or for all users)
    notifications = Notification.objects.filter(
        models.Q(user=request.user) | models.Q(user__isnull=True)
    ).order_by('-created_at')
    
    # Automatically mark all unread notifications as read when user visits this page
    Notification.objects.filter(
        models.Q(user=request.user) | models.Q(user__isnull=True),
        is_read=False
    ).update(is_read=True)
    
    context = {
        'current_year': datetime.now().year,
        'notifications': notifications
    }
    return render(request, 'notifications.html', context)


@login_required
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    from django.db import models
    if request.method == 'POST':
        try:
            notification = Notification.objects.filter(
                models.Q(user=request.user) | models.Q(user__isnull=True)
            ).get(id=notification_id)
            notification.is_read = True
            notification.save()
            return JsonResponse({'success': True})
        except Notification.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Notification not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def profile_view(request):
    """User profile view with edit functionality"""
    # Ensure user has a profile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Update user information
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.username = request.POST.get('username', request.user.username)
        request.user.email = request.POST.get('email', request.user.email)
        
        # Update profile bio
        profile.bio = request.POST.get('bio', '')
        
        # Handle profile image upload
        if 'profile_image' in request.FILES:
            image = request.FILES['profile_image']
            
            # Delete old image if exists
            if profile.profile_image:
                try:
                    os.remove(profile.profile_image.path)
                except:
                    pass
            
            # Save new image
            profile.profile_image = image
            
            # Optionally resize image to save space
            try:
                img = Image.open(profile.profile_image.path)
                if img.height > 500 or img.width > 500:
                    output_size = (500, 500)
                    img.thumbnail(output_size)
                    img.save(profile.profile_image.path)
            except:
                pass
        
        try:
            request.user.save()
            profile.save()
            messages.success(request, 'Profile updated successfully!')
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
        
        return redirect('profile')
    
    context = {
        'current_year': datetime.now().year
    }
    return render(request, 'profile.html', context)


@login_required
def settings_view(request):
    """User settings view with password change and preferences"""
    # Ensure user has a profile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'password':
            # Handle password change
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            # Validate current password
            if not request.user.check_password(current_password):
                messages.error(request, 'Current password is incorrect.')
            elif new_password != confirm_password:
                messages.error(request, 'New passwords do not match.')
            elif len(new_password) < 8:
                messages.error(request, 'Password must be at least 8 characters long.')
            else:
                # Update password
                request.user.set_password(new_password)
                request.user.save()
                update_session_auth_hash(request, request.user)  # Keep user logged in
                messages.success(request, 'Password changed successfully!')
        
        elif form_type == 'notifications':
            # Handle notification preferences
            profile.email_transactions = 'email_transactions' in request.POST
            profile.email_security = 'email_security' in request.POST
            profile.email_marketing = 'email_marketing' in request.POST
            profile.save()
            messages.success(request, 'Notification preferences updated!')
        
        elif form_type == '2fa':
            # Handle 2FA toggle
            profile.two_factor_enabled = not profile.two_factor_enabled
            profile.save()
            status = 'enabled' if profile.two_factor_enabled else 'disabled'
            messages.success(request, f'Two-factor authentication {status}!')
        
        return redirect('settings')
    
    context = {
        'current_year': datetime.now().year
    }
    return render(request, 'settings.html', context)


@login_required
def portfolio_view(request):
    """Portfolio page view - displays user's actual cryptocurrency holdings from UserWallet"""
    # Get user's wallet balances (same as dashboard)
    user_wallets = UserWallet.objects.filter(user=request.user).select_related('crypto_asset')
    
    # Get total balance from UserProfile (what admin manages)
    total_value = request.user.profile.wallet_balance if hasattr(request.user, 'profile') else Decimal('0')
    
    # Calculate portfolio metrics
    holdings = []
    
    for wallet in user_wallets:
        if wallet.balance > 0:  # Only include non-zero balances
            asset = wallet.crypto_asset
            # Balance is in USD, calculate crypto amount using current price
            crypto_amount = wallet.balance / asset.current_price if asset.current_price > 0 else Decimal('0')
            
            holdings.append({
                'id': wallet.id,
                'name': asset.name,
                'symbol': asset.symbol,
                'icon': asset.icon,
                'icon_url': asset.icon_url,
                'color': asset.color,
                'balance': float(crypto_amount),  # Crypto amount
                'value': float(wallet.balance),  # USD value
                'current_price': float(asset.current_price),
                'percentage_change': asset.percentage_change,
                'is_positive_change': asset.is_positive_change,
                'base_price': float(asset.base_price),
            })
    
    holdings.sort(key=lambda x: x['value'], reverse=True)
    
    top_holdings = []
    for holding in holdings[:5]:
        holding_copy = holding.copy()
        holding_copy['portfolio_percentage'] = (holding['value'] / float(total_value) * 100) if total_value > 0 else 0
        holding_copy['portfolio_value'] = holding['value']
        top_holdings.append(holding_copy)
    
    total_base_value = Decimal('0')
    for holding in holdings:
        crypto_amount = Decimal(str(holding['balance']))
        base_price = Decimal(str(holding['base_price']))
        total_base_value += crypto_amount * base_price
    
    total_gain = float(total_value - total_base_value)
    total_gain_percentage = (total_gain / float(total_base_value) * 100) if total_base_value > 0 else 0
    
    if holdings:
        best_performer = max(holdings, key=lambda x: x['percentage_change'])
        worst_performer = min(holdings, key=lambda x: x['percentage_change'])
    else:
        best_performer = None
        worst_performer = None
    
    current_value = float(total_value)
    base_value = float(total_base_value)
    
    # 24H data (hourly intervals)
    performance_24h = generate_performance_data(base_value, current_value, 24, 0.05)
    
    # 7D data (daily intervals)
    performance_7d = generate_performance_data(base_value, current_value, 7, 0.15)
    
    # 1M data (daily intervals, 30 points)
    performance_1m = generate_performance_data(base_value, current_value, 30, 0.25)
    
    # 1Y data (monthly intervals, 12 points)
    performance_1y = generate_performance_data(base_value * 0.7, current_value, 12, 0.40)
    
    # ALL data (yearly intervals, assume 3 years)
    performance_all = generate_performance_data(base_value * 0.5, current_value, 36, 0.50)
    
    context = {
        'current_year': datetime.now().year,
        'holdings': holdings,
        'top_holdings': top_holdings,
        'total_balance': float(total_value),
        'total_invested': float(total_base_value),
        'total_gain': total_gain,
        'total_gain_percentage': total_gain_percentage,
        'is_total_profit': total_gain >= 0,
        'total_assets': len(holdings),
        'best_performer': best_performer,
        'worst_performer': worst_performer,
        'daily_change': abs(total_gain * 0.15),  # Simulated daily volatility
        'performance_24h': performance_24h,
        'performance_7d': performance_7d,
        'performance_1m': performance_1m,
        'performance_1y': performance_1y,
        'performance_all': performance_all,
        'has_holdings': len(holdings) > 0,
    }
    return render(request, 'portfolio.html', context)


def generate_performance_data(start_value, end_value, num_points, volatility_factor):
    """Generate realistic performance data with volatility"""
    if start_value <= 0:
        return {
            'labels': [str(i) for i in range(num_points)],
            'data': [0] * num_points
        }
    
    data = []
    total_change = end_value - start_value
    
    for i in range(num_points):
        progress = i / (num_points - 1) if num_points > 1 else 1
        
        # Base value progression
        value = start_value + (total_change * progress)
        
        # Add volatility (oscillation that decreases as we approach the end)
        if i < num_points - 1:  # Don't add volatility to the last point
            volatility = start_value * volatility_factor * (1 - progress * 0.5)
            oscillation = volatility * (0.5 - abs(0.5 - (i % 4) / 4))
            value += oscillation
        
        data.append(round(value, 2))
    
    # Ensure last point is exactly the end value
    data[-1] = end_value
    
    # Generate labels based on number of points
    if num_points <= 24:
        labels = [f'{i}h' if i > 0 else 'Now' for i in range(num_points)]
    elif num_points <= 31:
        labels = [f'Day {i+1}' for i in range(num_points)]
    elif num_points <= 12:
        labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][:num_points]
    else:
        labels = [f'M{i+1}' for i in range(num_points)]
    
    return {
        'labels': labels,
        'data': data
    }


@login_required
def explore_view(request):
    """Explore markets page view"""
    crypto_assets = CryptoAsset.objects.all().order_by('order')
    
    # Category mappings for filtering
    category_map = {
        'BTC': ['all', 'trending', 'favorites'],
        'ETH': ['all', 'trending', 'favorites', 'defi'],
        'XLM': ['all'],
        'USDT': ['all', 'favorites'],
        'HBAR': ['all', 'gainers'],
        'BNB': ['all', 'trending', 'defi'],
        'SOL': ['all', 'trending', 'gainers', 'defi', 'nft'],
        'XRP': ['all', 'gainers'],
        'ADA': ['all', 'defi'],
        'DOGE': ['all', 'trending', 'gainers'],
        'DOT': ['all', 'defi'],
        'MATIC': ['all', 'gainers', 'defi', 'nft'],
        'LTC': ['all'],
        'AVAX': ['all', 'gainers', 'defi', 'nft'],
        'GOLD': ['all', 'losers'],
        'TSLA-X': ['all', 'trending', 'gainers'],
        'SPXAI': ['all', 'trending', 'gainers'],
        'PAIMON': ['all', 'gainers'],
    }
    
    # Add market data and categories for display
    assets_with_data = []
    for asset in crypto_assets:
        asset.week_change = asset.percentage_change * 1.2  # Simulated 7-day change
        asset.market_cap = asset.current_price * 1000000  # Simulated market cap in billions
        asset.volume_24h = asset.current_price * 50000  # Simulated 24h volume in millions
        
        # Assign categories based on performance
        categories = category_map.get(asset.symbol, ['all'])
        
        # Auto-categorize as gainer or loser based on percentage change
        if asset.percentage_change > 5 and 'gainers' not in categories:
            categories.append('gainers')
        elif asset.percentage_change < 0 and 'losers' not in categories:
            categories.append('losers')
        
        asset.categories = ','.join(categories)
        assets_with_data.append(asset)
    
    # Get trending assets (top 4 by percentage change)
    trending_assets = sorted(crypto_assets, key=lambda x: x.percentage_change, reverse=True)[:4]
    for trending in trending_assets:
        trending.week_change = trending.percentage_change * 1.2
    
    context = {
        'current_year': datetime.now().year,
        'crypto_assets': assets_with_data,
        'trending_assets': trending_assets,
    }
    return render(request, 'explore.html', context)


@login_required
def more_view(request):
    """More options page view"""
    # Get unread notification count
    notification_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    context = {
        'current_year': datetime.now().year,
        'notification_count': notification_count,
    }
    return render(request, 'more.html', context)


@login_required
def help_center_view(request):
    """Help Center page view"""
    context = {
        'current_year': datetime.now().year,
    }
    return render(request, 'help_center.html', context)


@login_required
def contact_support_view(request):
    """Contact Support page view - handles both GET (display form) and POST (submit form)"""
    from .models import ContactMessage
    from .translations import TRANSLATIONS
    from django.utils.translation import get_language
    
    # Get current language
    language = get_language()
    if language and '-' in language:
        language = language.split('-')[0]
    if not language or language not in TRANSLATIONS:
        language = 'en'
    
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message_text = request.POST.get('message')
        
        if name and email and subject and message_text:
            # Create contact message
            ContactMessage.objects.create(
                user=request.user,
                name=name,
                email=email,
                subject=subject,
                message=message_text,
                status='new'
            )
            messages.success(request, TRANSLATIONS[language]['message_sent_success'])
            return redirect('contact_support')
        else:
            messages.error(request, TRANSLATIONS[language]['fill_required_fields'])
    
    context = {
        'current_year': datetime.now().year,
    }
    return render(request, 'contact_support.html', context)


@login_required
def about_view(request):
    """About page view"""
    context = {
        'current_year': datetime.now().year,
    }
    return render(request, 'about.html', context)


@login_required
def asset_detail_view(request, symbol):
    """Asset detail page view"""
    from django.shortcuts import get_object_or_404
    from itertools import chain
    from operator import attrgetter
    
    asset = get_object_or_404(CryptoAsset, symbol=symbol)
    
    # Get user's wallet for this asset
    user_wallet = UserWallet.objects.filter(user=request.user, crypto_asset=asset).first()
    user_balance_usd = float(user_wallet.balance) if user_wallet else 0
    
    # Calculate crypto amount from USD balance
    crypto_amount = user_balance_usd / float(asset.current_price) if asset.current_price > 0 else 0
    
    # Get all transactions for this asset
    receive_txs = ReceiveTransaction.objects.filter(
        user=request.user, 
        crypto_asset=asset,
        status='confirmed'
    ).select_related('crypto_asset')
    
    sell_txs = SellTransaction.objects.filter(
        user=request.user, 
        crypto_asset=asset,
        status='confirmed'
    ).select_related('crypto_asset')
    
    # Swap transactions (both from and to this asset)
    swap_from_txs = SwapTransaction.objects.filter(
        user=request.user,
        from_crypto=asset
    ).select_related('from_crypto', 'to_crypto')
    
    swap_to_txs = SwapTransaction.objects.filter(
        user=request.user,
        to_crypto=asset
    ).select_related('from_crypto', 'to_crypto')
    
    # Combine and sort all transactions by date, adding type info
    transactions_list = []
    
    for tx in receive_txs:
        transactions_list.append({
            'type': 'receive',
            'data': tx,
            'created_at': tx.created_at
        })
    
    for tx in sell_txs:
        transactions_list.append({
            'type': 'sell',
            'data': tx,
            'created_at': tx.created_at
        })
    
    for tx in swap_from_txs:
        transactions_list.append({
            'type': 'swap_from',
            'data': tx,
            'created_at': tx.created_at
        })
    
    for tx in swap_to_txs:
        transactions_list.append({
            'type': 'swap_to',
            'data': tx,
            'created_at': tx.created_at
        })
    
    # Sort by date
    all_transactions = sorted(transactions_list, key=lambda x: x['created_at'], reverse=True)
    
    context = {
        'current_year': datetime.now().year,
        'asset': asset,
        'user_balance_usd': user_balance_usd,
        'crypto_amount': crypto_amount,
        'transactions': all_transactions,
    }
    return render(request, 'asset_detail.html', context)
