from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.models import Interesse, Livro, Reserva

from .forms import LivroForm


def index(request: HttpRequest) -> HttpResponse:

    livros_destaque = Livro.objects.filter(ativo=True).order_by("-id")[:3]

    contexto = {
        "titulo_pagina": "Estante Circular",
        "descricao": "Uma comunidade para compartilhar livros e fazer histórias continuarem circulando.",
        "livros_destaque": livros_destaque,
    }

    return render(request, "core/index.html", contexto)


def cadastro_view(request: HttpRequest) -> HttpResponse:
    contexto = {}

    if request.method == "POST":
        nome = request.POST.get("nome", "").strip()
        sobrenome = request.POST.get("sobrenome", "").strip()
        email = request.POST.get("email", "").strip()
        senha = request.POST.get("senha", "").strip()
        confirmar_senha = request.POST.get("confirmar_senha", "").strip()

        if senha != confirmar_senha:
            contexto["erro"] = "As senhas informadas não coincidem."
            return render(request, "core/cadastro.html", contexto)

        if User.objects.filter(username=email).exists():
            contexto["erro"] = "Já existe uma conta cadastrada com este e-mail."
            return render(request, "core/cadastro.html", contexto)

        User.objects.create_user(
            username=email,
            email=email,
            password=senha,
            first_name=nome,
            last_name=sobrenome,
        )

        return redirect("core:login")

    return render(request, "core/cadastro.html", contexto)


def login_view(request: HttpRequest) -> HttpResponse:
    contexto = {}

    next_url = request.GET.get("next", "")

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        senha = request.POST.get("senha", "")

        usuario = authenticate(request=request, username=email, password=senha)

        if usuario is not None:
            login(request=request, user=usuario)

            messages.success(request=request, message="Login realizado com sucesso.")

            if next_url:
                return redirect(next_url)

            return redirect("core:index")
        else:
            contexto["erro"] = "E-mail ou senha inválidos."

    return render(request, "core/login.html", contexto)


def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request=request)

    messages.info(request=request, message="Você saiu da sua conta.")

    return redirect("core:index")


@login_required
def disponibilizar_livro(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = LivroForm(request.POST)

        if form.is_valid():  # validação dos campos do formulário
            livro = form.save(
                commit=False
            )  # cria o objeto Livro sem salvar no banco de dados ainda
            livro.responsavel = (
                request.user
            )  # atribui o usuário logado como responsável pelo livro
            livro.save()  # salva o objeto Livro no banco de dados

            messages.success(
                request=request,
                message="Livro disponibilizado com sucesso.",
            )

            return redirect(
                "core:detalhes_livro",
                id=livro.pk,
            )
    else:
        form = LivroForm()

    contexto = {
        "form": form,
    }

    return render(
        request=request,
        template_name="core/disponibilizar_livro.html",
        context=contexto,
    )


def catalogo(request: HttpRequest) -> HttpResponse:
    termo_busca = request.GET.get(
        "busca",
        "",
    ).strip()

    livros = Livro.objects.filter(ativo=True)

    if termo_busca:
        livros = livros.filter(
            ativo=True,
            titulo__icontains=termo_busca,  # lookup
        )

    """
    icontains significa:
    conter o texto + ignorar diferença entre maiúsculas e minúsculas
    """

    contexto = {
        "livros": livros,
        "termo_busca": termo_busca,
        "pesquisa_realizada": bool(termo_busca),
    }

    return render(
        request,
        "core/catalogo.html",
        contexto,
    )


def detalhes_livro(request: HttpRequest, id: int) -> HttpResponse:

    livro = Livro.objects.filter(ativo=True, id=id).first()

    if livro is None:
        return HttpResponse(
            "Livro não encontrado.",
            status=404,
        )

    interesses = []

    if request.user.is_authenticated and livro.responsavel == request.user:
        interesses = livro.interesses.select_related("interessado").order_by( # type: ignore
            "-data_interesse"
        )

    reserva_ativa = (
        Reserva.objects.filter(interesse__livro=livro, status=Reserva.Status.ATIVA)
        .select_related("interesse", "interesse__interessado")
        .first()
    )

    contexto = {
        "livro": livro,
        "interesses": interesses,
        "reserva_ativa": reserva_ativa,
    }

    return render(
        request,
        "core/detalhes_livro.html",
        contexto,
    )


@login_required
def editar_livro(request: HttpRequest, id: int) -> HttpResponse:
    livro = get_object_or_404(
        Livro.objects.select_related("responsavel"), ativo=True, pk=id
    )

    if livro.responsavel != request.user:
        raise PermissionDenied("Você não tem permissão para editar este livro.")

    if request.method == "POST":
        form = LivroForm(
            request.POST,
            instance=livro,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Livro atualizado com sucesso.",
            )

            return redirect(
                "core:detalhes_livro",
                id=livro.pk,
            )

    else:
        form = LivroForm(
            instance=livro,
        )

    contexto = {
        "livro": livro,
        "form": form,
    }

    return render(
        request,
        "core/editar_livro.html",
        contexto,
    )


@login_required
def excluir_livro(request: HttpRequest, id: int) -> HttpResponse:
    livro = get_object_or_404(Livro, id=id, ativo=True)

    if livro.responsavel != request.user:
        raise PermissionDenied("Você não tem permissão para remover este livro.")

    if request.method == "POST":
        livro.ativo = False
        livro.save()

        messages.success(request=request, message="Livro removido com sucesso.")

        return redirect("core:meus_livros")

    contexto = {"livro": livro}

    return render(
        request=request, template_name="core/excluir_livro.html", context=contexto
    )


@login_required
def meus_livros(request: HttpRequest) -> HttpResponse:

    livros = Livro.objects.filter(responsavel=request.user).order_by("-id")

    contexto = {"livros": livros}

    return render(
        request=request, template_name="core/meus_livros.html", context=contexto
    )


@login_required
@require_POST
def demonstrar_interesse(request: HttpRequest, id: int) -> HttpResponse:
    livro = get_object_or_404(Livro, pk=id, ativo=True)

    if livro.situacao != Livro.Situacao.DISPONIVEL:
        messages.warning(
            request=request,
            message="Este livro não está disponível para novos de interesses.",
        )
        return redirect("core:detalhes_livro", id=livro.pk)

    if livro.responsavel == request.user:
        messages.error(
            request=request,
            message="Você não pode demonstrar interesse em um livro que você mesmo disponibilizou.",
        )
        return redirect("core:detalhes_livro", id=livro.pk)

    _, status_criado = Interesse.objects.get_or_create(
        livro=livro,
        interessado=request.user,
    )

    if status_criado:
        messages.success(
            request=request,
            message="Seu interesse no livro foi registrado com sucesso.",
        )
    else:
        messages.info(
            request=request,
            message="Você já demonstrou interesse neste livro.",
        )

    return redirect("core:detalhes_livro", id=livro.pk)


@login_required
@require_POST
def aceitar_interesse(request: HttpRequest, id: int) -> HttpResponse:

    # Recupera o interesse pelo ID, garantindo que o livro e os usuários relacionados sejam carregados para evitar consultas adicionais ao banco de dados.
    interesse = get_object_or_404(
        Interesse.objects.select_related("livro", "livro__responsavel", "interessado"),
        pk=id,
    )

    # HTTP 403 Forbidden: Se o usuário logado não for o responsável pelo livro, ele não tem permissão para aceitar o interesse.
    if interesse.livro.responsavel != request.user:
        raise PermissionDenied("Você não tem permissão para aceitar este interesse.")

    # Regra de negócio / estado: Se o interesse já foi processado (aceito ou recusado), não é possível aceitá-lo novamente.
    if interesse.status != Interesse.Status.PENDENTE:
        messages.warning(
            request=request,
            message="Este interesse já foi processado.",
        )
        return redirect("core:detalhes_livro", id=interesse.livro.pk)

    interesse.status = Interesse.Status.ACEITO

    interesse.save(update_fields=["status"])

    messages.success(
        request=request,
        message=f"Interesse de {interesse.interessado.username} no livro '{interesse.livro.titulo}' foi aceito.",
    )

    return redirect("core:detalhes_livro", id=interesse.livro.pk)


@login_required
@require_POST
def recusar_interesse(request: HttpRequest, id: int) -> HttpResponse:
    interesse = get_object_or_404(
        Interesse.objects.select_related("livro", "livro__responsavel", "interessado"),
        pk=id,
    )

    if interesse.livro.responsavel != request.user:
        raise PermissionDenied("Você não tem permissão para recusar este interesse.")

    if interesse.status != Interesse.Status.PENDENTE:
        messages.warning(
            request=request,
            message="Este interesse já foi processado.",
        )
        return redirect("core:detalhes_livro", id=interesse.livro.pk)

    interesse.status = Interesse.Status.RECUSADO

    interesse.save(update_fields=["status"])

    messages.success(
        request=request,
        message=f"Interesse de {interesse.interessado.username} no livro '{interesse.livro.titulo}' foi recusado.",
    )

    return redirect("core:detalhes_livro", id=interesse.livro.pk)


@login_required
def meus_interesses(request: HttpRequest) -> HttpResponse:
    interesses = (
        Interesse.objects
        .filter(interessado=request.user)
        .select_related("livro", "livro__responsavel")
        .prefetch_related("reservas",)
        .order_by("-data_interesse")
    )

    # O contexto é um dicionário que contém os dados que serão passados para o template. Neste caso, estamos passando a lista de interesses do usuário logado.
    contexto = {
        "interesses": interesses,
    }

    return render(
        request=request, template_name="core/meus_interesses.html", context=contexto
    )


@login_required
@require_POST
def reservar_livro(request: HttpRequest, id: int) -> HttpResponse:
    interesse = get_object_or_404(
        Interesse.objects.select_related("livro", "livro__responsavel", "interessado"),
        pk=id,
    )

    if interesse.livro.responsavel != request.user:
        raise PermissionDenied("Você não tem permissão para reservar este livro.")

    if interesse.status != Interesse.Status.ACEITO:
        messages.warning(
            request=request,
            message="Somente interesses aceitos podem ser reservados.",
        )
        return redirect("core:detalhes_livro", id=interesse.livro.pk)

    if not interesse.livro.ativo:
        messages.warning(
            request=request,
            message="Este livro não está mais disponível para reserva.",
        )
        return redirect("core:detalhes_livro", id=interesse.livro.pk)

    if interesse.livro.situacao != Livro.Situacao.DISPONIVEL:
        messages.warning(
            request=request,
            message="Este livro já está reservado ou emprestado e não pode ser reservado novamente.",
        )
        return redirect("core:detalhes_livro", id=interesse.livro.pk)

    reserva_ativa = Reserva.objects.filter(
        interesse__livro=interesse.livro, status=Reserva.Status.ATIVA
    ).exists()

    if reserva_ativa:
        messages.info(
            request=request,
            message="Você já possui uma reserva ativa para este livro.",
        )

        return redirect("core:detalhes_livro", id=interesse.livro.pk)

    Reserva.objects.create(
        interesse=interesse,
    )

    interesse.livro.situacao = Livro.Situacao.RESERVADO
    interesse.livro.save(update_fields=["situacao"])

    messages.success(
        request=request,
        message=f"Reserva do livro '{interesse.livro.titulo}' realizada com sucesso.",
    )

    return redirect("core:detalhes_livro", id=interesse.livro.pk)


@login_required
@require_POST
def cancelar_reserva(request: HttpRequest, id: int) -> HttpResponse:
    reserva = get_object_or_404(
        Reserva.objects.select_related(
            "interesse",
            "interesse__livro",
            "interesse__livro__responsavel",
            "interesse__interessado",
        ),
        pk=id,
    )

    if request.user not in (
        reserva.interesse.interessado,
        reserva.interesse.livro.responsavel,
    ):
        raise PermissionDenied("Você não tem permissão para cancelar esta reserva.")

    if reserva.status != Reserva.Status.ATIVA:
        messages.warning(
            request=request,
            message="Está reserva não está ativa.",
        )
        return redirect("core:detalhes_livro", id=reserva.interesse.livro.pk)

    reserva.status = Reserva.Status.CANCELADA
    reserva.encerrada_em = timezone.now()
    reserva.save(update_fields=["status", "encerrada_em"])

    reserva.interesse.livro.situacao = Livro.Situacao.DISPONIVEL
    reserva.interesse.livro.save(update_fields=["situacao"])

    messages.success(
        request=request,
        message=f"Reserva do livro '{reserva.interesse.livro.titulo}' cancelada com sucesso.",
    )

    return redirect("core:detalhes_livro", id=reserva.interesse.livro.pk)


# =========================================================
# TRATAMENTO DE ERROS
# =========================================================


def erro_400(
    request: HttpRequest,
    exception,
) -> HttpResponse:

    contexto = {
        "codigo_erro": "400",
        "titulo_erro": "Requisição inválida",
        "mensagem_erro": (
            "Não foi possível processar a solicitação "
            "enviada. Verifique os dados e tente novamente."
        ),
    }

    return render(
        request,
        "core/erro.html",
        contexto,
        status=400,
    )


def erro_403(
    request: HttpRequest,
    exception,
) -> HttpResponse:

    contexto = {
        "codigo_erro": "403",
        "titulo_erro": "Acesso não permitido",
        "mensagem_erro": (
            "Você está autenticado, mas não possui permissão para acessar este recurso."
        ),
    }

    return render(
        request,
        "core/erro.html",
        contexto,
        status=403,
    )


def erro_404(
    request: HttpRequest,
    exception,
) -> HttpResponse:

    contexto = {
        "codigo_erro": "404",
        "titulo_erro": "Página não encontrada",
        "mensagem_erro": (
            "O conteúdo que você tentou acessar "
            "não foi encontrado ou não está mais disponível."
        ),
    }

    return render(
        request,
        "core/erro.html",
        contexto,
        status=404,
    )


def erro_500(
    request: HttpRequest,
) -> HttpResponse:

    contexto = {
        "codigo_erro": "500",
        "titulo_erro": "Ocorreu um erro inesperado",
        "mensagem_erro": (
            "Não foi possível concluir a operação neste momento. "
            "Tente novamente em alguns instantes."
        ),
    }

    return render(
        request,
        "core/erro.html",
        contexto,
        status=500,
    )
