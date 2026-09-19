from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.models import Emprestimo, Interesse, Livro, Reserva

from .forms import LivroForm, ReservaForm


def _nome_usuario(usuario) -> str:
    return usuario.get_full_name() or usuario.username


def index(request: HttpRequest) -> HttpResponse:
    livros_destaque = (
        Livro.objects.filter(
            ativo=True,
            situacao=Livro.Situacao.DISPONIVEL,
        )
        .select_related("responsavel")
        .order_by("-id")[:3]
    )

    contexto = {
        "titulo_pagina": "Estante Circular",
        "descricao": (
            "Uma comunidade para compartilhar livros, conectar leitores "
            "e manter boas histórias em circulação."
        ),
        "livros_destaque": livros_destaque,
    }
    return render(request, "core/index.html", contexto)


def cadastro_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("core:index")

    contexto = {
        "dados": {
            "nome": "",
            "sobrenome": "",
            "email": "",
        }
    }

    if request.method == "POST":
        nome = request.POST.get("nome", "").strip()
        sobrenome = request.POST.get("sobrenome", "").strip()
        email = request.POST.get("email", "").strip().lower()
        senha = request.POST.get("senha", "")
        confirmar_senha = request.POST.get("confirmar_senha", "")

        contexto["dados"] = {
            "nome": nome,
            "sobrenome": sobrenome,
            "email": email,
        }

        if not nome or not sobrenome or not email or not senha:
            contexto["erro"] = "Preencha todos os campos obrigatórios."
            return render(request, "core/cadastro.html", contexto)

        try:
            validate_email(email)
        except ValidationError:
            contexto["erro"] = "Informe um endereço de e-mail válido."
            return render(request, "core/cadastro.html", contexto)

        if senha != confirmar_senha:
            contexto["erro"] = "As senhas informadas não coincidem."
            return render(request, "core/cadastro.html", contexto)

        if User.objects.filter(username__iexact=email).exists():
            contexto["erro"] = "Já existe uma conta cadastrada com este e-mail."
            return render(request, "core/cadastro.html", contexto)

        usuario_temporario = User(
            username=email,
            email=email,
            first_name=nome,
            last_name=sobrenome,
        )

        try:
            validate_password(senha, user=usuario_temporario)
        except ValidationError as exc:
            contexto["erro"] = " ".join(exc.messages)
            return render(request, "core/cadastro.html", contexto)

        User.objects.create_user(
            username=email,
            email=email,
            password=senha,
            first_name=nome,
            last_name=sobrenome,
        )

        messages.success(
            request,
            "Conta criada com sucesso. Entre com seu e-mail e senha.",
        )
        return redirect("core:login")

    return render(request, "core/cadastro.html", contexto)


def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("core:index")

    next_url = request.POST.get("next") or request.GET.get("next", "")
    contexto = {
        "next": next_url,
        "email": "",
    }

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        senha = request.POST.get("senha", "")
        contexto["email"] = email

        usuario = authenticate(request=request, username=email, password=senha)

        if usuario is None:
            contexto["erro"] = "E-mail ou senha inválidos."
            return render(request, "core/login.html", contexto)

        login(request=request, user=usuario)
        messages.success(request, "Acesso realizado com sucesso.")

        if next_url and url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)

        return redirect("core:index")

    return render(request, "core/login.html", contexto)


@login_required
@require_POST
def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    messages.info(request, "Você saiu da sua conta.")
    return redirect("core:index")


@login_required
def disponibilizar_livro(request: HttpRequest) -> HttpResponse:
    form = LivroForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        livro = form.save(commit=False)
        livro.responsavel = request.user
        livro.save()

        messages.success(request, "Livro disponibilizado com sucesso.")
        return redirect("core:detalhes_livro", id=livro.pk)

    return render(
        request,
        "core/disponibilizar_livro.html",
        {"form": form},
    )


def catalogo(request: HttpRequest) -> HttpResponse:
    termo_busca = request.GET.get("busca", "").strip()

    livros = (
        Livro.objects.filter(ativo=True)
        .select_related("responsavel")
        .order_by("-id")
    )

    if termo_busca:
        livros = livros.filter(
            Q(titulo__icontains=termo_busca)
            | Q(autor__icontains=termo_busca)
            | Q(genero__icontains=termo_busca)
        )

    contexto = {
        "livros": livros,
        "termo_busca": termo_busca,
        "pesquisa_realizada": bool(termo_busca),
    }
    return render(request, "core/catalogo.html", contexto)


def detalhes_livro(request: HttpRequest, id: int) -> HttpResponse:
    livro = get_object_or_404(
        Livro.objects.select_related("responsavel"),
        pk=id,
        ativo=True,
    )

    contexto = {
        "livro": livro,
        "interesses": [],
        "reservas_pendentes": [],
        "reserva_ativa": None,
        "emprestimo_ativo": None,
        "interesse_usuario": None,
    }

    if request.user.is_authenticated:
        if livro.responsavel == request.user:
            contexto["interesses"] = (
                livro.interesses.select_related("interessado")
                .prefetch_related("reservas")
                .order_by("-data_interesse")
            )
            contexto["reservas_pendentes"] = (
                Reserva.objects.filter(
                    interesse__livro=livro,
                    status=Reserva.Status.PENDENTE,
                )
                .select_related("interesse", "interesse__interessado")
                .order_by("data_retirada_prevista", "data_reserva")
            )
            contexto["reserva_ativa"] = (
                Reserva.objects.filter(
                    interesse__livro=livro,
                    status=Reserva.Status.APROVADA,
                )
                .select_related("interesse", "interesse__interessado")
                .first()
            )
            contexto["emprestimo_ativo"] = (
                Emprestimo.objects.filter(
                    reserva__interesse__livro=livro,
                    status=Emprestimo.Status.ATIVO,
                )
                .select_related(
                    "reserva",
                    "reserva__interesse",
                    "reserva__interesse__interessado",
                )
                .first()
            )
        else:
            contexto["interesse_usuario"] = (
                Interesse.objects.filter(
                    livro=livro,
                    interessado=request.user,
                )
                .prefetch_related("reservas")
                .first()
            )

    return render(request, "core/detalhes_livro.html", contexto)


@login_required
def editar_livro(request: HttpRequest, id: int) -> HttpResponse:
    livro = get_object_or_404(
        Livro.objects.select_related("responsavel"),
        ativo=True,
        pk=id,
    )

    if livro.responsavel != request.user:
        raise PermissionDenied("Você não tem permissão para editar este livro.")

    if livro.situacao != Livro.Situacao.DISPONIVEL:
        messages.warning(
            request,
            "O livro não pode ser editado enquanto estiver reservado ou emprestado.",
        )
        return redirect("core:detalhes_livro", id=livro.pk)

    form = LivroForm(request.POST or None, instance=livro)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Informações do livro atualizadas.")
        return redirect("core:detalhes_livro", id=livro.pk)

    return render(
        request,
        "core/editar_livro.html",
        {"livro": livro, "form": form},
    )


@login_required
def excluir_livro(request: HttpRequest, id: int) -> HttpResponse:
    livro = get_object_or_404(Livro, pk=id, ativo=True)

    if livro.responsavel != request.user:
        raise PermissionDenied("Você não tem permissão para remover este livro.")

    if livro.situacao != Livro.Situacao.DISPONIVEL:
        messages.warning(
            request,
            "O livro não pode ser removido enquanto estiver reservado ou emprestado.",
        )
        return redirect("core:detalhes_livro", id=livro.pk)

    if request.method == "POST":
        livro.ativo = False
        livro.save(update_fields=["ativo"])
        messages.success(request, "Livro removido do catálogo.")
        return redirect("core:meus_livros")

    return render(request, "core/excluir_livro.html", {"livro": livro})


@login_required
def meus_livros(request: HttpRequest) -> HttpResponse:
    livros = (
        Livro.objects.filter(responsavel=request.user)
        .prefetch_related(
            Prefetch(
                "interesses",
                queryset=Interesse.objects.filter(status=Interesse.Status.PENDENTE),
                to_attr="interesses_pendentes",
            )
        )
        .order_by("-id")
    )
    return render(request, "core/meus_livros.html", {"livros": livros})


@login_required
@require_POST
def demonstrar_interesse(request: HttpRequest, id: int) -> HttpResponse:
    livro = get_object_or_404(Livro, pk=id, ativo=True)

    if livro.situacao != Livro.Situacao.DISPONIVEL:
        messages.warning(
            request,
            "Este livro não está disponível para novos interesses no momento.",
        )
        return redirect("core:detalhes_livro", id=livro.pk)

    if livro.responsavel == request.user:
        messages.error(
            request,
            "Você não pode demonstrar interesse em um livro que disponibilizou.",
        )
        return redirect("core:detalhes_livro", id=livro.pk)

    interesse, criado = Interesse.objects.get_or_create(
        livro=livro,
        interessado=request.user,
    )

    if criado:
        messages.success(request, "Seu interesse foi registrado.")
    elif interesse.status == Interesse.Status.PENDENTE:
        messages.info(request, "Seu interesse neste livro já está aguardando análise.")
    elif interesse.status == Interesse.Status.ACEITO:
        messages.info(request, "Seu interesse neste livro já foi aceito.")
    else:
        messages.info(request, "Já existe um registro de interesse seu para este livro.")

    return redirect("core:detalhes_livro", id=livro.pk)


@login_required
@require_POST
def aceitar_interesse(request: HttpRequest, id: int) -> HttpResponse:
    interesse = get_object_or_404(
        Interesse.objects.select_related("livro", "livro__responsavel", "interessado"),
        pk=id,
    )

    if interesse.livro.responsavel != request.user:
        raise PermissionDenied("Você não tem permissão para aceitar este interesse.")

    if interesse.status != Interesse.Status.PENDENTE:
        messages.warning(request, "Este interesse já foi processado.")
        return redirect("core:detalhes_livro", id=interesse.livro.pk)

    if not interesse.livro.ativo:
        messages.warning(request, "O livro não está mais ativo no catálogo.")
        return redirect("core:meus_livros")

    interesse.status = Interesse.Status.ACEITO
    interesse.save(update_fields=["status"])

    messages.success(
        request,
        f"Interesse de {_nome_usuario(interesse.interessado)} aceito. "
        "Agora a pessoa poderá solicitar uma reserva.",
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
        messages.warning(request, "Este interesse já foi processado.")
        return redirect("core:detalhes_livro", id=interesse.livro.pk)

    interesse.status = Interesse.Status.RECUSADO
    interesse.save(update_fields=["status"])

    messages.info(
        request,
        f"Interesse de {_nome_usuario(interesse.interessado)} recusado.",
    )
    return redirect("core:detalhes_livro", id=interesse.livro.pk)


@login_required
def meus_interesses(request: HttpRequest) -> HttpResponse:
    interesses = (
        Interesse.objects.filter(interessado=request.user)
        .select_related("livro", "livro__responsavel")
        .prefetch_related("reservas", "reservas__emprestimo")
        .order_by("-data_interesse")
    )
    return render(
        request,
        "core/meus_interesses.html",
        {"interesses": interesses},
    )


@login_required
def solicitar_reserva(request: HttpRequest, id: int) -> HttpResponse:
    interesse = get_object_or_404(
        Interesse.objects.select_related("livro", "livro__responsavel", "interessado"),
        pk=id,
    )
    livro = interesse.livro

    if interesse.interessado != request.user:
        raise PermissionDenied("Você não tem permissão para solicitar esta reserva.")

    if interesse.status != Interesse.Status.ACEITO:
        messages.warning(
            request,
            "A reserva só pode ser solicitada depois que o interesse for aceito.",
        )
        return redirect("core:meus_interesses")

    if not livro.ativo or livro.situacao != Livro.Situacao.DISPONIVEL:
        messages.warning(request, "Este livro não está disponível para reserva.")
        return redirect("core:meus_interesses")

    if Reserva.objects.filter(
        interesse=interesse,
        status__in=[Reserva.Status.PENDENTE, Reserva.Status.APROVADA],
    ).exists():
        messages.info(request, "Já existe uma reserva em andamento para este interesse.")
        return redirect("core:meus_interesses")

    form = ReservaForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        reserva = form.save(commit=False)
        reserva.interesse = interesse
        reserva.save()

        messages.success(
            request,
            "Solicitação de reserva enviada. Aguarde a confirmação do responsável.",
        )
        return redirect("core:meus_interesses")

    return render(
        request,
        "core/solicitar_reserva.html",
        {"form": form, "interesse": interesse, "livro": livro},
    )


@login_required
@require_POST
def aprovar_reserva(request: HttpRequest, id: int) -> HttpResponse:
    reserva = get_object_or_404(
        Reserva.objects.select_related(
            "interesse",
            "interesse__livro",
            "interesse__livro__responsavel",
            "interesse__interessado",
        ),
        pk=id,
    )
    livro = reserva.interesse.livro

    if livro.responsavel != request.user:
        raise PermissionDenied("Você não tem permissão para aprovar esta reserva.")

    if reserva.status != Reserva.Status.PENDENTE:
        messages.warning(request, "Esta solicitação já foi processada.")
        return redirect("core:detalhes_livro", id=livro.pk)

    with transaction.atomic():
        livro = Livro.objects.select_for_update().get(pk=livro.pk)

        if not livro.ativo or livro.situacao != Livro.Situacao.DISPONIVEL:
            messages.warning(request, "Este livro não está mais disponível para reserva.")
            return redirect("core:detalhes_livro", id=livro.pk)

        agora = timezone.now()

        reserva.status = Reserva.Status.APROVADA
        reserva.data_aprovacao = agora
        reserva.save(update_fields=["status", "data_aprovacao"])

        livro.situacao = Livro.Situacao.RESERVADO
        livro.save(update_fields=["situacao"])

        Reserva.objects.filter(
            interesse__livro=livro,
            status=Reserva.Status.PENDENTE,
        ).exclude(pk=reserva.pk).update(
            status=Reserva.Status.RECUSADA,
            data_encerramento=agora,
        )

    messages.success(
        request,
        f"Reserva aprovada para {_nome_usuario(reserva.interesse.interessado)}.",
    )
    return redirect("core:detalhes_livro", id=livro.pk)


@login_required
@require_POST
def recusar_reserva(request: HttpRequest, id: int) -> HttpResponse:
    reserva = get_object_or_404(
        Reserva.objects.select_related(
            "interesse",
            "interesse__livro",
            "interesse__livro__responsavel",
        ),
        pk=id,
    )
    livro = reserva.interesse.livro

    if livro.responsavel != request.user:
        raise PermissionDenied("Você não tem permissão para recusar esta reserva.")

    if reserva.status != Reserva.Status.PENDENTE:
        messages.warning(request, "Esta solicitação já foi processada.")
        return redirect("core:detalhes_livro", id=livro.pk)

    reserva.status = Reserva.Status.RECUSADA
    reserva.data_encerramento = timezone.now()
    reserva.save(update_fields=["status", "data_encerramento"])

    messages.info(request, "Solicitação de reserva recusada.")
    return redirect("core:detalhes_livro", id=livro.pk)


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
    livro = reserva.interesse.livro

    if request.user not in (reserva.interesse.interessado, livro.responsavel):
        raise PermissionDenied("Você não tem permissão para cancelar esta reserva.")

    if reserva.status not in (Reserva.Status.PENDENTE, Reserva.Status.APROVADA):
        messages.warning(request, "Esta reserva não pode mais ser cancelada.")
        return redirect(
            "core:detalhes_livro" if request.user == livro.responsavel else "core:meus_interesses",
            **({"id": livro.pk} if request.user == livro.responsavel else {}),
        )

    with transaction.atomic():
        status_anterior = reserva.status
        reserva.status = Reserva.Status.CANCELADA
        reserva.data_encerramento = timezone.now()
        reserva.save(update_fields=["status", "data_encerramento"])

        if status_anterior == Reserva.Status.APROVADA:
            livro.situacao = Livro.Situacao.DISPONIVEL
            livro.save(update_fields=["situacao"])

    messages.success(request, "Reserva cancelada.")

    if request.user == livro.responsavel:
        return redirect("core:detalhes_livro", id=livro.pk)
    return redirect("core:meus_interesses")


@login_required
@require_POST
def iniciar_emprestimo(request: HttpRequest, id: int) -> HttpResponse:
    reserva = get_object_or_404(
        Reserva.objects.select_related(
            "interesse",
            "interesse__livro",
            "interesse__livro__responsavel",
            "interesse__interessado",
        ),
        pk=id,
    )
    livro = reserva.interesse.livro

    if livro.responsavel != request.user:
        raise PermissionDenied("Você não tem permissão para iniciar este empréstimo.")

    if reserva.status != Reserva.Status.APROVADA:
        messages.warning(request, "Esta reserva não está aprovada para retirada.")
        return redirect("core:detalhes_livro", id=livro.pk)

    if livro.situacao != Livro.Situacao.RESERVADO:
        messages.warning(request, "O livro não está registrado como reservado.")
        return redirect("core:detalhes_livro", id=livro.pk)

    if Emprestimo.objects.filter(reserva=reserva).exists():
        messages.warning(request, "Esta reserva já possui um empréstimo associado.")
        return redirect("core:detalhes_livro", id=livro.pk)

    with transaction.atomic():
        Emprestimo.objects.create(reserva=reserva)

        reserva.status = Reserva.Status.CONCLUIDA
        reserva.data_encerramento = timezone.now()
        reserva.save(update_fields=["status", "data_encerramento"])

        livro.situacao = Livro.Situacao.EMPRESTADO
        livro.save(update_fields=["situacao"])

    messages.success(request, "Entrega confirmada. O empréstimo está ativo.")
    return redirect("core:detalhes_livro", id=livro.pk)


@login_required
@require_POST
def devolver_livro(request: HttpRequest, id: int) -> HttpResponse:
    emprestimo = get_object_or_404(
        Emprestimo.objects.select_related(
            "reserva",
            "reserva__interesse",
            "reserva__interesse__livro",
            "reserva__interesse__livro__responsavel",
            "reserva__interesse__interessado",
        ),
        pk=id,
    )
    livro = emprestimo.reserva.interesse.livro

    if livro.responsavel != request.user:
        raise PermissionDenied("Você não tem permissão para confirmar esta devolução.")

    if emprestimo.status != Emprestimo.Status.ATIVO:
        messages.warning(request, "Este empréstimo já foi encerrado.")
        return redirect("core:detalhes_livro", id=livro.pk)

    if livro.situacao != Livro.Situacao.EMPRESTADO:
        messages.warning(request, "O livro não está registrado como emprestado.")
        return redirect("core:detalhes_livro", id=livro.pk)

    with transaction.atomic():
        emprestimo.status = Emprestimo.Status.DEVOLVIDO
        emprestimo.devolvido_em = timezone.now()
        emprestimo.save(update_fields=["status", "devolvido_em"])

        livro.situacao = Livro.Situacao.DISPONIVEL
        livro.save(update_fields=["situacao"])

    messages.success(
        request,
        "Devolução registrada. O livro voltou a ficar disponível.",
    )
    return redirect("core:detalhes_livro", id=livro.pk)


@login_required
@require_POST
def marcar_nao_retirada(request: HttpRequest, id: int) -> HttpResponse:
    reserva = get_object_or_404(
        Reserva.objects.select_related(
            "interesse",
            "interesse__livro",
            "interesse__livro__responsavel",
        ),
        pk=id,
    )
    livro = reserva.interesse.livro

    if livro.responsavel != request.user:
        raise PermissionDenied("Você não tem permissão para alterar esta reserva.")

    if reserva.status != Reserva.Status.APROVADA:
        messages.warning(request, "Esta reserva não está aguardando retirada.")
        return redirect("core:detalhes_livro", id=livro.pk)

    if timezone.localdate() <= reserva.data_retirada_prevista:
        messages.warning(
            request,
            "A data prevista para retirada ainda não foi ultrapassada.",
        )
        return redirect("core:detalhes_livro", id=livro.pk)

    with transaction.atomic():
        reserva.status = Reserva.Status.NAO_RETIRADA
        reserva.data_encerramento = timezone.now()
        reserva.save(update_fields=["status", "data_encerramento"])

        livro.situacao = Livro.Situacao.DISPONIVEL
        livro.save(update_fields=["situacao"])

    messages.info(
        request,
        "Não retirada registrada. O livro voltou a ficar disponível.",
    )
    return redirect("core:detalhes_livro", id=livro.pk)


@login_required
def historico_livro(request: HttpRequest, id: int) -> HttpResponse:
    livro = get_object_or_404(
        Livro.objects.select_related("responsavel"),
        pk=id,
    )

    if livro.responsavel != request.user:
        raise PermissionDenied(
            "Você não tem permissão para visualizar o histórico deste livro."
        )

    interesses = (
        livro.interesses.select_related("interessado")
        .prefetch_related("reservas", "reservas__emprestimo")
        .order_by("-data_interesse")
    )

    return render(
        request,
        "core/historico_livro.html",
        {"livro": livro, "interesses": interesses},
    )


def erro_400(request: HttpRequest, exception) -> HttpResponse:
    return render(
        request,
        "core/erro.html",
        {
            "codigo_erro": "400",
            "titulo_erro": "Solicitação inválida",
            "mensagem_erro": (
                "Não foi possível processar a solicitação. "
                "Revise as informações e tente novamente."
            ),
        },
        status=400,
    )


def erro_403(request: HttpRequest, exception) -> HttpResponse:
    return render(
        request,
        "core/erro.html",
        {
            "codigo_erro": "403",
            "titulo_erro": "Acesso não autorizado",
            "mensagem_erro": (
                "Sua conta não possui permissão para realizar esta operação."
            ),
        },
        status=403,
    )


def erro_404(request: HttpRequest, exception) -> HttpResponse:
    return render(
        request,
        "core/erro.html",
        {
            "codigo_erro": "404",
            "titulo_erro": "Página não encontrada",
            "mensagem_erro": (
                "O conteúdo solicitado não existe ou não está mais disponível."
            ),
        },
        status=404,
    )


def erro_500(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "core/erro.html",
        {
            "codigo_erro": "500",
            "titulo_erro": "Não foi possível concluir a operação",
            "mensagem_erro": (
                "Ocorreu um erro inesperado. Tente novamente em alguns instantes."
            ),
        },
        status=500,
    )
