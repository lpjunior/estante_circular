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
        'livros/<int:id>/excluir/',
        views.excluir_livro,
        name='excluir_livro'
    ),
    path(
        'livros/<int:id>/interesse/',
        views.demonstrar_interesse,
        name='demonstrar_interesse',
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
    path(
        'meus-livros/',
        views.meus_livros,
        name='meus_livros',
    ),
    path(
        'interesses/<int:id>/aceitar/',
        views.aceitar_interesse,
        name='aceitar_interesse',
    ),
    path(
        'interesses/<int:id>/recusar/',
        views.recusar_interesse,
        name='recusar_interesse',
    ),
    path(
        'meus-interesses/',
        views.meus_interesses,
        name='meus_interesses'
    ),
    path(
        'interesses/<int:id>/reservar/',
        views.reservar_livro,
        name='reservar_livro',
    ),
    path(
        'reservas/<int:id>/cancelar/',
        views.cancelar_reserva,
        name='cancelar_reserva',
    ),
]