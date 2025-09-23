"""
BSV Middleware for Django

A Django middleware library for BSV blockchain authentication and payment processing.
Based on Express middleware implementation with py-sdk integration.
"""

__version__ = "0.1.0"
__author__ = "BSV Middleware Team"
__email__ = "team@bsv-middleware.com"

from .django.auth_middleware import BSVAuthMiddleware
from .django.payment_middleware import BSVPaymentMiddleware

__all__ = [
    "BSVAuthMiddleware",
    "BSVPaymentMiddleware",
]