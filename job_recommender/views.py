from django.shortcuts import render

# Create your views here.
def landing_page(request):
    return render(request, 'landing_page.html')

def career_form(request):
    return render(request, 'career_form.html')


    