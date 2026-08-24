from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

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

    next_url = request.GET.get('next', '')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        senha = request.POST.get('senha', '')

        usuario = authenticate(
            request=request,
            username=email,
            password=senha
        )

        if usuario is not None:
            login(request=request, user=usuario)

            if next_url:
                return redirect(next_url)

            return redirect('core:index')
        else:
            contexto['erro'] = 'E-mail ou senha inválidos.'

    return render(request, 'core/login.html', contexto)

def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request=request)
    return redirect('core:index')

@login_required(login_url='core:login')
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

@login_required(login_url='core:login')
def editar_livro(request: HttpRequest, id: int) -> HttpResponse:
    livro = get_object_or_404(Livro, id=id)

    if request.method == 'POST':
        livro.titulo = request.POST.get('titulo', '').strip()
        livro.autor = request.POST.get('autor', '').strip()
        livro.genero = request.POST.get('genero', '').strip()
        livro.estado_conservacao = request.POST.get('estado_conservacao', '').strip()
        livro.responsavel = request.POST.get('responsavel', '').strip()
        livro.descricao = request.POST.get('descricao', '').strip()

        livro.save()

        return redirect(
            'core:detalhes_livro',
            id=livro.id,
        )

    contexto = {
        'livro': livro,
    }

    return render(
        request,
        'core/editar_livro.html',
        contexto
    )

def cadastro_view(request: HttpRequest) -> HttpResponse:
    contexto = {}

    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        sobrenome = request.POST.get('sobrenome', '').strip()
        email = request.POST.get('email', '').strip()
        senha = request.POST.get('senha', '').strip()
        confirmar_senha = request.POST.get('confirmar_senha', '').strip()

        if senha != confirmar_senha:
            contexto['erro'] = ('As senhas informadas não coincidem.')
            return render(request, 'core/cadastro.html', contexto)


        if User.objects.filter(username=email).exists():
            contexto['erro'] = ('Já existe uma conta cadastrada com este e-mail.')
            return render(request, 'core/cadastro.html', contexto)

        User.objects.create_user(
            username=email,
            email=email,
            password=senha,
            first_name=nome,
            last_name=sobrenome
        )

        return redirect('core:login')
    
    return render(request, 'core/cadastro.html', contexto)