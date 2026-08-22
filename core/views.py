import os

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from core.models import Livro


def index (request: HttpRequest) -> HttpResponse:

    livros_destaque = Livro.objects.order_by('-id')[:3]

    contexto = {
        'titulo_pagina': 'Estante Circular',
        'descricao': 'Uma comunidade para compartilhar livros e fazer histórias continuarem circulando.',
        'livros_destaque': livros_destaque,
    }

    return render(request, 'core/index.html', contexto)

def login_view(request: HttpRequest) -> HttpResponse:
    contexto = {}

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        senha = request.POST.get('senha', '')

        email_mock = os.getenv('MOCK_LOGIN_EMAIL')
        senha_mock = os.getenv('MOCK_LOGIN_PASSWORD')

        if email == email_mock and senha == senha_mock:
            contexto['login_realizado'] = True
            contexto['email_usuario'] = email
        else:
            contexto['erro'] = 'E-mail ou senha inválidos.'

    return render(request, 'core/login.html', contexto)


def disponibilizar_livro(request: HttpRequest) -> HttpResponse:
    contexto = {}

    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        autor = request.POST.get('autor', '').strip()
        genero = request.POST.get('genero', '').strip()
        estado_conservacao = request.POST.get('estado_conservacao', '').strip()
        responsavel = request.POST.get('responsavel', '').strip()
        descricao = request.POST.get('descricao', '').strip()

        livro = Livro.objects.create(
            titulo=titulo,
            autor=autor,
            genero=genero,
            estado_conservacao=estado_conservacao,
            responsavel=responsavel,
            descricao=descricao,
        )

        contexto = {
            'livro_enviado': True,
            'livro': livro,
        }

    return render(
        request,
        'core/disponibilizar_livro.html',
        contexto,
    )

def catalogo(request: HttpRequest) -> HttpResponse:
    termo_busca = request.GET.get(
        'busca',
        '',
    ).strip()

    livros = Livro.objects.all()

    if termo_busca:
        livros = livros.filter(
            titulo__icontains=termo_busca, # lookup
        )

    """
    icontains significa:
    conter o texto + ignorar diferença entre maiúsculas e minúsculas
    """


    contexto = {
        'livros': livros,
        'termo_busca': termo_busca,
        'pesquisa_realizada': bool(termo_busca),
    }

    return render(
        request,
        'core/catalogo.html',
        contexto,
    )


def detalhes_livro(request: HttpRequest, id: int) -> HttpResponse:

    contexto = {}

    livro = Livro.objects.filter(id=id).first()

    if livro is None:
        return HttpResponse(
            'Livro não encontrado.',
            status=404,
        )

    contexto = {
        'livro': livro,
    }

    return render(
        request, 
        'core/detalhes_livro.html',
        contexto,
    )