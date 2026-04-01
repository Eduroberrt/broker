from django import template
from app.models import UserPriceOverride

register = template.Library()

@register.filter
def user_price(asset, user):
    """Get the price for an asset considering user-specific XRP overrides"""
    if not user or not user.is_authenticated:
        return asset.current_price
    
    if asset.symbol == 'XRP':
        try:
            override = UserPriceOverride.objects.get(user=user)
            if override.xrp_custom_price:
                return override.xrp_custom_price
        except UserPriceOverride.DoesNotExist:
            pass
    
    return asset.current_price


@register.filter
def user_formatted_price(asset, user):
    """Get formatted price for an asset considering user-specific XRP overrides"""
    price = float(user_price(asset, user))
    
    if price < 1:
        return f"${price:.4f}"
    elif price < 100:
        return f"${price:.2f}"
    else:
        return f"${price:,.2f}"
