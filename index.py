"""
Vercel WSGI entry point for the Flask application
"""

from app import app

# Vercel calls this as the handler
def handler(request):
    return app(request)
