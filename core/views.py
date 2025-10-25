from django.shortcuts import render
from django.shortcuts import render, redirect
from .forms import ModelsForm
from .models import Models
# Create your views here.
from django.shortcuts import render

def home(request):
    return render(request, 'home.html')

def cadastro(request):
    if request.method == "POST":
        form = ModelsForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("cadastro")  # ou redirecionar para uma tela de sucesso
    else:
        form = ModelsForm()

    return render(request, "cadastro.html", {"form": form})

