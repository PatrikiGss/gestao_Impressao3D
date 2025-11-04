from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('cadastro/', views.cadastro, name='cadastro'),
    path('sucesso/', views.sucesso, name='sucesso'),
    path('lista/', views.lista_models, name='lista_models'),
    path('download/<int:pk>/', views.download_arquivo, name='download_arquivo'),
    path('excluir/<int:pk>/', views.excluir, name='excluir'),
    path('atualizar-status/<int:pk>/<str:novo_status>/', views.atualizar_status, name='atualizar_status'),
]
