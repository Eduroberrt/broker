from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.contrib.auth.models import User
from datetime import datetime
from django.http import JsonResponse
from .models import CryptoAsset, ReceiveTransaction, UserWallet, SwapTransaction, SellTransaction, Notification


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
    crypto_assets = CryptoAsset.objects.all()
    
    # Get user's wallet balances
    user_wallets = UserWallet.objects.filter(user=request.user).select_related('crypto_asset')
    
    # Create a dictionary for quick wallet lookup by crypto_asset id
    wallet_dict = {wallet.crypto_asset.id: wallet.balance for wallet in user_wallets}
    
    # Calculate total wallet value (balance is already in USD)
    total_balance = sum(wallet.balance for wallet in user_wallets)
    
    context = {
        'current_year': datetime.now().year,
        'crypto_assets': crypto_assets,
        'wallet_dict': wallet_dict,
        'total_balance': total_balance,
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
                
                # Create receive transaction
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
            
            # Get user's wallet for FROM crypto
            from_wallet = UserWallet.objects.filter(user=request.user, crypto_asset=from_crypto).first()
            
            if not from_wallet or from_wallet.balance < from_amount_usd:
                return JsonResponse({'success': False, 'message': 'Insufficient balance'})
            
            # Calculate TO amount (same USD value)
            to_amount_usd = from_amount_usd
            
            # Deduct from FROM wallet
            from_wallet.balance -= from_amount_usd
            from_wallet.save()
            
            # Add to TO wallet
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
    crypto_assets = CryptoAsset.objects.all()
    
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
