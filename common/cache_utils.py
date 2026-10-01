from django.core.cache import cache
from functools import wraps
import hashlib
import json


def cache_key(prefix, *args, **kwargs):
    """Generate a unique cache key from prefix and arguments."""
    key_parts = [prefix]
    key_parts.extend(str(arg) for arg in args)

    if kwargs:
        key_parts.append(json.dumps(kwargs, sort_keys=True))

    key_string = ':'.join(key_parts)
    # Hash long keys to stay under memcached key length limits
    if len(key_string) > 250:
        return f"{prefix}:{hashlib.md5(key_string.encode()).hexdigest()}"
    return key_string


def cache_result(timeout=3600):
    """
    Decorator to cache function results.

    Args:
        timeout: Cache timeout in seconds (default 3600)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key from function name and arguments
            key = cache_key(
                f"{func.__module__}:{func.__name__}",
                *args,
                **kwargs
            )

            # Try to get from cache
            result = cache.get(key)
            if result is not None:
                return result

            # Calculate result and cache it
            result = func(*args, **kwargs)
            cache.set(key, result, timeout)
            return result

        wrapper.cache_key = lambda *args, **kwargs: cache_key(
            f"{func.__module__}:{func.__name__}",
            *args,
            **kwargs
        )
        wrapper.clear_cache = lambda *args, **kwargs: cache.delete(
            cache_key(f"{func.__module__}:{func.__name__}", *args, **kwargs)
        )
        return wrapper
    return decorator


def invalidate_cache_pattern(pattern):
    """
    Invalidate all cache keys matching a pattern.
    Note: This works efficiently with Redis but less so with local memory cache.
    """
    if hasattr(cache, 'delete_pattern'):
        cache.delete_pattern(pattern)
    else:
        # Fallback for backends that don't support pattern deletion
        pass


def clear_cache_by_prefix(prefix):
    """Clear all cache entries with a given prefix."""
    try:
        if hasattr(cache, '_cache') and hasattr(cache._cache, '_cache'):
            # LocMemCache
            keys_to_delete = [key for key in cache._cache._cache.keys() if key.startswith(prefix)]
            for key in keys_to_delete:
                cache.delete(key)
        elif hasattr(cache, 'delete_pattern'):
            # Redis with django_redis
            cache.delete_pattern(f"{prefix}:*")
    except Exception:
        pass


def cache_queryset(cache_key, timeout=3600):
    """
    Decorator to cache querysets in ViewSet get_queryset() method.

    Args:
        cache_key: Cache key to use for storing the queryset
        timeout: Cache timeout in seconds (default 3600)

    Usage:
        @cache_queryset('diagnostic_centre_list', timeout=3600)
        def get_queryset(self):
            return DiagnosticCentre.objects.all()
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Only cache for list action
            if self.action == 'list':
                cached_queryset = cache.get(cache_key)
                if cached_queryset is not None:
                    return cached_queryset

                queryset = func(self, *args, **kwargs)
                cache.set(cache_key, queryset, timeout)
                return queryset

            return func(self, *args, **kwargs)

        return wrapper
    return decorator


def cache_user_queryset(cache_key_prefix, timeout=300):
    """
    Decorator to cache user-specific querysets in ViewSet get_queryset() method.

    Args:
        cache_key_prefix: Prefix for cache key (user ID will be appended)
        timeout: Cache timeout in seconds (default 300)

    Usage:
        @cache_user_queryset('user_bookings', timeout=300)
        def get_queryset(self):
            return Booking.objects.filter(user=self.request.user)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Only cache for list action
            if self.action == 'list':
                user_cache_key = f'{cache_key_prefix}:{self.request.user.id}'
                cached_queryset = cache.get(user_cache_key)
                if cached_queryset is not None:
                    return cached_queryset

                queryset = func(self, *args, **kwargs)
                cache.set(user_cache_key, queryset, timeout)
                return queryset

            return func(self, *args, **kwargs)

        return wrapper
    return decorator
