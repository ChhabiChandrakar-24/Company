from django.shortcuts import render, get_object_or_404
from .models import Quotation

def quotation_list(request):
    """Render a list of all quotations."""
    quotations = Quotation.objects.all().order_by('-created_at')
    return render(request, "quotations/quotation_list.html", {"quotations": quotations})

def quotation_detail(request, number):
    """Render details for a specific quotation identified by its number."""
    quotation = get_object_or_404(Quotation, number=number)
    return render(request, "quotations/quotation_detail.html", {"quotation": quotation})

# Create your views here.
