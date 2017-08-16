from django.shortcuts import render
from django.views.generic import TemplateView


class IndexView(TemplateView):
    """Main view for site."""
    
    template_name = 'rankings/index.html'

