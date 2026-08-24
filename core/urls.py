from django.urls import path

from core import views

app_name = 'core'


urlpatterns = [
    path('', 
         views.index, 
         name='index'
    ),

    path(
        'catalogo/',
        views.catalogo,
        name='catalogo',
    ),
    path(
        'disponibilizar/',
        views.disponibilizar_livro,
        name='disponibilizar_livro',
    ),
    path(
        'livros/<int:id>',
        views.detalhes_livro,
        name='detalhes_livro'
    ),
    path(
        'livros/<int:id>/editar/',
        views.editar_livro,
        name='editar_livro'
    ),
    path(
        'login/',
        views.login_view,
        name='login',
    ),
    path(
        'logout/',
        views.logout_view,
        name='logout',
    ),
    path(
        'cadastro/',
        views.cadastro_view,
        name='cadastro',
    ),
]