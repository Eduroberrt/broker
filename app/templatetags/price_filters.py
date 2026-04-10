from django import template
from app.models import UserPriceOverride

register = template.Library()

@register.filter
def user_price(asset, user):
    """Get the price for an asset considering user-specific XRP and TSLAx overrides"""
    if not user or not user.is_authenticated:
        return asset.current_price
    
    # Check for XRP override
    if asset.symbol == 'XRP':
        try:
            override = UserPriceOverride.objects.get(user=user)
            if override.xrp_custom_price:
                return override.xrp_custom_price
        except UserPriceOverride.DoesNotExist:
            pass
    
    # Check for TSLAx override
    if asset.symbol == 'TSLAx':
        try:
            override = UserPriceOverride.objects.get(user=user)
            if override.tslax_custom_price:
                return override.tslax_custom_price
        except UserPriceOverride.DoesNotExist:
            pass
    
    return asset.current_price


@register.filter
def user_formatted_price(asset, user):
    """Get formatted price for an asset considering user-specific XRP and TSLAx overrides"""
    price = float(user_price(asset, user))
    
    if price < 1:
        return f"${price:.4f}"
    elif price < 100:
        return f"${price:.2f}"
    else:
        return f"${price:,.2f}"
