from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import AlterarDataReservaForm, LivroForm, ReservaForm
from .models import Emprestimo, Interesse, Livro, PropostaReserva, Reserva

User = get_user_model()


def index(request: HttpRequest) -> HttpResponse:
    livros_destaque = (
        Livro.objects.filter(ativo=True, situacao=Livro.Situacao.DISPONIVEL)
        .select_related("responsavel")
        .order_by("-pk")[:3]
    )
    return render(
        request,
        "core/index.html",
        {
            "titulo_pagina": "Livros que continuam circulando",
            "descricao": (
                "Compartilhe livros, encontre novas leituras e ajude histórias "
                "a continuarem circulando."
            ),
            "livros_destaque": livros_destaque,
        },
    )


def catalogo(request: HttpRequest) -> HttpResponse:
    termo_busca = request.GET.get("busca", "").strip()
    livros = (
        Livro.objects.filter(ativo=True).select_related("responsavel").order_by("-pk")
    )
    if termo_busca:
        livros = livros.filter(
            Q(titulo__icontains=termo_busca)
            | Q(autor__icontains=termo_busca)
            | Q(genero__icontains=termo_busca)
        )
    return render(
        request,
        "core/catalogo.html",
        {
            "livros": livros,
            "termo_busca": termo_busca,
            "pesquisa_realizada": bool(termo_busca),
        },
    )


def detalhes_livro(request: HttpRequest, id: int) -> HttpResponse:
    livro = get_object_or_404(
        Livro.objects.select_related("responsavel"),
        pk=id,
        ativo=True,
    )

    interesses = Interesse.objects.none()
    reservas_pendentes = Reserva.objects.none()
    reservas_aguardando_interessado = Reserva.objects.none()
    interesse_usuario = None

    if request.user.is_authenticated:
        if livro.responsavel == request.user:
            interesses = livro.interesses.select_related("interessado").order_by(
                "data_interesse"
            )
            reservas_pendentes = (
                Reserva.objects.filter(
                    interesse__livro=livro,
                    status=Reserva.Status.AGUARDANDO_RESPONSAVEL,
                )
                .select_related("interesse", "interesse__interessado")
                .prefetch_related("propostas")
                .order_by("data_retirada_prevista")
            )
            reservas_aguardando_interessado = (
                Reserva.objects.filter(
                    interesse__livro=livro,
                    status=Reserva.Status.AGUARDANDO_INTERESSADO,
                )
                .select_related("interesse", "interesse__interessado")
                .prefetch_related("propostas")
                .order_by("data_retirada_prevista")
            )
        else:
            interesse_usuario = Interesse.objects.filter(
                livro=livro, interessado=request.user
            ).first()

    reserva_ativa = (
        Reserva.objects.filter(
            interesse__livro=livro,
            status=Reserva.Status.APROVADA,
        )
        .select_related("interesse", "interesse__interessado")
        .first()
    )
    emprestimo_ativo = (
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

    return render(
        request,
        "core/detalhes_livro.html",
        {
            "livro": livro,
            "interesses": interesses,
            "interesse_usuario": interesse_usuario,
            "reservas_pendentes": reservas_pendentes,
            "reservas_aguardando_interessado": reservas_aguardando_interessado,
            "reserva_ativa": reserva_ativa,
            "emprestimo_ativo": emprestimo_ativo,
        },
    )


def cadastro_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("core:index")

    contexto = {}
    if request.method == "POST":
        nome = request.POST.get("nome", "").strip()
        sobrenome = request.POST.get("sobrenome", "").strip()
        email = request.POST.get("email", "").strip().lower()
        senha = request.POST.get("senha", "")
        confirmar_senha = request.POST.get("confirmar_senha", "")

        if not all([nome, sobrenome, email, senha, confirmar_senha]):
            contexto["erro"] = "Preencha todos os campos."
        elif senha != confirmar_senha:
            contexto["erro"] = "As senhas informadas não são iguais."
        elif User.objects.filter(username__iexact=email).exists():
            contexto["erro"] = "Já existe uma conta cadastrada com este e-mail."
        else:
            User.objects.create_user(
                username=email,
                email=email,
                password=senha,
                first_name=nome,
                last_name=sobrenome,
            )
            messages.success(
                request,
                "Conta criada com sucesso. Faça login para continuar.",
            )
            return redirect("core:login")

    return render(request, "core/cadastro.html", contexto)


def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("core:index")

    next_url = request.POST.get("next") or request.GET.get("next") or ""
    contexto = {"next": next_url}

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        senha = request.POST.get("senha", "")
        usuario = authenticate(request, username=email, password=senha)

        if usuario is None:
            contexto["erro"] = "E-mail ou senha inválidos."
            return render(request, "core/login.html", contexto)

        auth_login(request, usuario)
        messages.success(request, "Login realizado com sucesso.")
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
    auth_logout(request)
    messages.info(request, "Você saiu da sua conta.")
    return redirect("core:index")


@login_required
def disponibilizar_livro(request: HttpRequest) -> HttpResponse:
    form = LivroForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        livro = form.save(commit=False)
        livro.responsavel = request.user
        livro.ativo = True
        livro.situacao = Livro.Situacao.DISPONIVEL
        livro.save()

        messages.success(request, "Livro disponibilizado com sucesso.")

        return redirect("core:detalhes_livro", id=livro.pk)

    return render(request, "core/disponibilizar_livro.html", {"form": form})


@login_required
def editar_livro(request: HttpRequest, id: int) -> HttpResponse:
    livro = get_object_or_404(
        Livro.objects.select_related("responsavel"), pk=id, ativo=True
    )
    if livro.responsavel != request.user:
        raise PermissionDenied("Você não tem permissão para editar este livro.")
    if livro.situacao != Livro.Situacao.DISPONIVEL:
        messages.warning(
            request,
            "Este livro não pode ser editado enquanto estiver reservado ou emprestado.",
        )
        return redirect("core:detalhes_livro", id=livro.pk)

    form = LivroForm(request.POST or None, request.FILES or None, instance=livro)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Livro atualizado com sucesso.")
        return redirect("core:detalhes_livro", id=livro.pk)

    return render(
        request,
        "core/editar_livro.html",
        {"livro": livro, "form": form},
    )


@login_required
def excluir_livro(request: HttpRequest, id: int) -> HttpResponse:
    livro = get_object_or_404(
        Livro.objects.select_related("responsavel"), pk=id, ativo=True
    )
    if livro.responsavel != request.user:
        raise PermissionDenied("Você não tem permissão para remover este livro.")
    if livro.situacao != Livro.Situacao.DISPONIVEL:
        messages.warning(
            request,
            "Este livro não pode ser removido enquanto estiver reservado ou emprestado.",
        )
        return redirect("core:detalhes_livro", id=livro.pk)
    if request.method == "POST":
        livro.ativo = False
        livro.save(update_fields=["ativo"])
        messages.success(request, "Livro removido do catálogo com sucesso.")
        return redirect("core:meus_livros")
    return render(request, "core/excluir_livro.html", {"livro": livro})


@login_required
def meus_livros(request: HttpRequest) -> HttpResponse:
    livros = Livro.objects.filter(responsavel=request.user).order_by("-pk")
    return render(request, "core/meus_livros.html", {"livros": livros})


@login_required
@require_POST
def demonstrar_interesse(request: HttpRequest, id: int) -> HttpResponse:
    livro = get_object_or_404(
        Livro.objects.select_related("responsavel"), pk=id, ativo=True
    )
    if livro.responsavel == request.user:
        messages.warning(
            request,
            "Você não pode demonstrar interesse em um livro disponibilizado por você.",
        )
    elif livro.situacao != Livro.Situacao.DISPONIVEL:
        messages.warning(
            request,
            "Este livro não está disponível para novos interesses.",
        )
    else:
        interesse, criado = Interesse.objects.get_or_create(
            livro=livro,
            interessado=request.user,
        )
        if criado:
            messages.success(request, "Interesse registrado com sucesso.")
        else:
            messages.info(request, "Você já demonstrou interesse neste livro.")
    return redirect("core:detalhes_livro", id=livro.pk)


@login_required
@require_POST
def aceitar_interesse(request: HttpRequest, id: int) -> HttpResponse:
    interesse = get_object_or_404(
        Interesse.objects.select_related("livro", "livro__responsavel", "interessado"),
        pk=id,
    )
    livro = interesse.livro
    if livro.responsavel != request.user:
        raise PermissionDenied("Você não tem permissão para aceitar este interesse.")
    if interesse.status != Interesse.Status.PENDENTE:
        messages.warning(request, "Este interesse já foi processado.")
    elif not livro.ativo or livro.situacao != Livro.Situacao.DISPONIVEL:
        messages.warning(request, "Este livro não está disponível neste momento.")
    else:
        interesse.status = Interesse.Status.ACEITO
        interesse.save(update_fields=["status"])
        messages.success(request, "Interesse aceito com sucesso.")
    return redirect("core:detalhes_livro", id=livro.pk)


@login_required
@require_POST
def recusar_interesse(request: HttpRequest, id: int) -> HttpResponse:
    interesse = get_object_or_404(
        Interesse.objects.select_related("livro", "livro__responsavel"), pk=id
    )
    livro = interesse.livro
    if livro.responsavel != request.user:
        raise PermissionDenied("Você não tem permissão para recusar este interesse.")
    if interesse.status != Interesse.Status.PENDENTE:
        messages.warning(request, "Este interesse já foi processado.")
    else:
        interesse.status = Interesse.Status.RECUSADO
        interesse.save(update_fields=["status"])
        messages.info(request, "Interesse recusado.")
    return redirect("core:detalhes_livro", id=livro.pk)


@login_required
def meus_interesses(request: HttpRequest) -> HttpResponse:
    interesses = (
        Interesse.objects.filter(interessado=request.user)
        .select_related("livro", "livro__responsavel")
        .prefetch_related("reservas", "reservas__propostas", "reservas__emprestimo")
        .order_by("-data_interesse")
    )
    return render(request, "core/meus_interesses.html", {"interesses": interesses})


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
        messages.warning(request, "Somente interesses aceitos podem gerar uma reserva.")
        return redirect("core:meus_interesses")
    if not livro.ativo or livro.situacao != Livro.Situacao.DISPONIVEL:
        messages.warning(
            request, "Este livro não está disponível para reserva neste momento."
        )
        return redirect("core:meus_interesses")

    if Reserva.objects.filter(
        interesse=interesse,
        status__in=[
            Reserva.Status.AGUARDANDO_RESPONSAVEL,
            Reserva.Status.AGUARDANDO_INTERESSADO,
            Reserva.Status.APROVADA,
        ],
    ).exists():
        messages.info(request, "Já existe uma reserva em andamento para este livro.")
        return redirect("core:meus_interesses")

    form = ReservaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            livro_bloqueado = Livro.objects.select_for_update().get(pk=livro.pk)
            if (
                not livro_bloqueado.ativo
                or livro_bloqueado.situacao != Livro.Situacao.DISPONIVEL
            ):
                messages.warning(
                    request, "O livro deixou de estar disponível para reserva."
                )
                return redirect("core:meus_interesses")

            reserva = form.save(commit=False)
            reserva.interesse = interesse
            reserva.status = Reserva.Status.AGUARDANDO_RESPONSAVEL
            reserva.save()
            PropostaReserva.objects.create(
                reserva=reserva,
                data_retirada=reserva.data_retirada_prevista,
                autor=PropostaReserva.Autor.INTERESSADO,
            )

        messages.success(
            request,
            "Solicitação de reserva enviada. Aguarde a resposta do responsável.",
        )
        return redirect("core:meus_interesses")

    return render(
        request,
        "core/solicitar_reserva.html",
        {"form": form, "interesse": interesse, "livro": livro},
    )


def _aprovar_reserva(reserva: Reserva, livro: Livro) -> None:
    agora = timezone.now()
    reserva.status = Reserva.Status.APROVADA
    reserva.data_aprovacao = agora
    reserva.save(update_fields=["status", "data_aprovacao"])

    livro.situacao = Livro.Situacao.RESERVADO
    livro.save(update_fields=["situacao"])

    (
        Reserva.objects.filter(
            interesse__livro=livro,
            status__in=[
                Reserva.Status.AGUARDANDO_RESPONSAVEL,
                Reserva.Status.AGUARDANDO_INTERESSADO,
            ],
        )
        .exclude(pk=reserva.pk)
        .update(
            status=Reserva.Status.CANCELADA,
            data_encerramento=agora,
        )
    )


@login_required
@require_POST
def aceitar_reserva_responsavel(request: HttpRequest, id: int) -> HttpResponse:
    with transaction.atomic():
        reserva = get_object_or_404(
            Reserva.objects.select_for_update().select_related(
                "interesse", "interesse__livro", "interesse__livro__responsavel"
            ),
            pk=id,
        )
        livro = Livro.objects.select_for_update().get(pk=reserva.interesse.livro.pk)
        if livro.responsavel != request.user:
            raise PermissionDenied("Você não tem permissão para aceitar esta reserva.")
        if reserva.status != Reserva.Status.AGUARDANDO_RESPONSAVEL:
            messages.warning(request, "Esta reserva não está aguardando sua resposta.")
            return redirect("core:detalhes_livro", id=livro.pk)
        if (
            not reserva.data_retirada_prevista
            or reserva.data_retirada_prevista < timezone.localdate()
        ):
            messages.warning(
                request, "A data proposta já passou. Informe uma nova data."
            )
            return redirect("core:detalhes_livro", id=livro.pk)
        if not livro.ativo or livro.situacao != Livro.Situacao.DISPONIVEL:
            messages.warning(request, "Este livro não está mais disponível.")
            return redirect("core:detalhes_livro", id=livro.pk)
        _aprovar_reserva(reserva, livro)

    messages.success(request, "Reserva aprovada. O livro está reservado.")
    return redirect("core:detalhes_livro", id=livro.pk)


@login_required
@require_POST
def aceitar_reserva_interessado(request: HttpRequest, id: int) -> HttpResponse:
    with transaction.atomic():
        reserva = get_object_or_404(
            Reserva.objects.select_for_update().select_related(
                "interesse", "interesse__livro", "interesse__interessado"
            ),
            pk=id,
        )
        livro = Livro.objects.select_for_update().get(pk=reserva.interesse.livro.pk)
        if reserva.interesse.interessado != request.user:
            raise PermissionDenied("Você não tem permissão para aceitar esta reserva.")
        if reserva.status != Reserva.Status.AGUARDANDO_INTERESSADO:
            messages.warning(request, "Esta reserva não está aguardando sua resposta.")
            return redirect("core:meus_interesses")
        if (
            not reserva.data_retirada_prevista
            or reserva.data_retirada_prevista < timezone.localdate()
        ):
            messages.warning(
                request, "A data proposta já passou. Informe uma nova data."
            )
            return redirect("core:meus_interesses")
        if not livro.ativo or livro.situacao != Livro.Situacao.DISPONIVEL:
            messages.warning(request, "Este livro não está mais disponível.")
            return redirect("core:meus_interesses")
        _aprovar_reserva(reserva, livro)

    messages.success(request, "Reserva aprovada. O livro foi reservado para você.")
    return redirect("core:meus_interesses")


def _registrar_nova_proposta(
    reserva: Reserva,
    nova_data,
    novo_status: str,
    autor: str,
) -> None:
    reserva.data_retirada_prevista = nova_data
    reserva.status = novo_status
    reserva.save(update_fields=["data_retirada_prevista", "status"])
    PropostaReserva.objects.create(
        reserva=reserva,
        data_retirada=nova_data,
        autor=autor,
    )


@login_required
def alterar_data_reserva_responsavel(request: HttpRequest, id: int) -> HttpResponse:
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
        raise PermissionDenied("Você não tem permissão para alterar esta reserva.")
    if reserva.status != Reserva.Status.AGUARDANDO_RESPONSAVEL:
        messages.warning(request, "Esta reserva não está aguardando sua resposta.")
        return redirect("core:detalhes_livro", id=livro.pk)
    if not livro.ativo or livro.situacao != Livro.Situacao.DISPONIVEL:
        messages.warning(request, "Este livro não está mais disponível.")
        return redirect("core:detalhes_livro", id=livro.pk)

    form = AlterarDataReservaForm(
        request.POST or None,
        initial={"data_retirada": reserva.data_retirada_prevista},
    )
    if request.method == "POST" and form.is_valid():
        nova_data = form.cleaned_data["data_retirada"]
        if nova_data == reserva.data_retirada_prevista:
            form.add_error(
                "data_retirada", "Informe uma data diferente da proposta atual."
            )
        else:
            with transaction.atomic():
                reserva = Reserva.objects.select_for_update().get(pk=reserva.pk)
                if reserva.status != Reserva.Status.AGUARDANDO_RESPONSAVEL:
                    messages.warning(
                        request, "A reserva foi atualizada por outra operação."
                    )
                    return redirect("core:detalhes_livro", id=livro.pk)
                _registrar_nova_proposta(
                    reserva,
                    nova_data,
                    Reserva.Status.AGUARDANDO_INTERESSADO,
                    PropostaReserva.Autor.RESPONSAVEL,
                )
            messages.success(request, "Nova data enviada ao interessado.")
            return redirect("core:detalhes_livro", id=livro.pk)

    return render(
        request,
        "core/alterar_data_reserva.html",
        {"form": form, "reserva": reserva, "livro": livro, "perfil": "responsavel"},
    )


@login_required
def alterar_data_reserva_interessado(request: HttpRequest, id: int) -> HttpResponse:
    reserva = get_object_or_404(
        Reserva.objects.select_related(
            "interesse", "interesse__livro", "interesse__interessado"
        ),
        pk=id,
    )
    livro = reserva.interesse.livro
    if reserva.interesse.interessado != request.user:
        raise PermissionDenied("Você não tem permissão para alterar esta reserva.")
    if reserva.status != Reserva.Status.AGUARDANDO_INTERESSADO:
        messages.warning(request, "Esta reserva não está aguardando sua resposta.")
        return redirect("core:meus_interesses")
    if not livro.ativo or livro.situacao != Livro.Situacao.DISPONIVEL:
        messages.warning(request, "Este livro não está mais disponível.")
        return redirect("core:meus_interesses")

    form = AlterarDataReservaForm(
        request.POST or None,
        initial={"data_retirada": reserva.data_retirada_prevista},
    )
    if request.method == "POST" and form.is_valid():
        nova_data = form.cleaned_data["data_retirada"]
        if nova_data == reserva.data_retirada_prevista:
            form.add_error(
                "data_retirada", "Informe uma data diferente da proposta atual."
            )
        else:
            with transaction.atomic():
                reserva = Reserva.objects.select_for_update().get(pk=reserva.pk)
                if reserva.status != Reserva.Status.AGUARDANDO_INTERESSADO:
                    messages.warning(
                        request, "A reserva foi atualizada por outra operação."
                    )
                    return redirect("core:meus_interesses")
                _registrar_nova_proposta(
                    reserva,
                    nova_data,
                    Reserva.Status.AGUARDANDO_RESPONSAVEL,
                    PropostaReserva.Autor.INTERESSADO,
                )
            messages.success(request, "Nova data enviada ao responsável.")
            return redirect("core:meus_interesses")

    return render(
        request,
        "core/alterar_data_reserva.html",
        {"form": form, "reserva": reserva, "livro": livro, "perfil": "interessado"},
    )


@login_required
@require_POST
def cancelar_reserva(request: HttpRequest, id: int) -> HttpResponse:
    with transaction.atomic():
        reserva = get_object_or_404(
            Reserva.objects.select_for_update().select_related(
                "interesse",
                "interesse__livro",
                "interesse__livro__responsavel",
                "interesse__interessado",
            ),
            pk=id,
        )
        livro = Livro.objects.select_for_update().get(pk=reserva.interesse.livro.pk)
        interessado = reserva.interesse.interessado
        responsavel = livro.responsavel

        aguardando_responsavel = (
            request.user == responsavel
            and reserva.status == Reserva.Status.AGUARDANDO_RESPONSAVEL
        )
        aguardando_interessado = (
            request.user == interessado
            and reserva.status == Reserva.Status.AGUARDANDO_INTERESSADO
        )
        reserva_aprovada = (
            request.user in (responsavel, interessado)
            and reserva.status == Reserva.Status.APROVADA
        )

        if not (aguardando_responsavel or aguardando_interessado or reserva_aprovada):
            raise PermissionDenied(
                "Você não tem permissão para cancelar esta reserva neste momento."
            )

        reserva.status = Reserva.Status.CANCELADA
        reserva.cancelada_por = request.user
        reserva.data_encerramento = timezone.now()
        reserva.save(update_fields=["status", "cancelada_por", "data_encerramento"])

        if reserva_aprovada and livro.situacao == Livro.Situacao.RESERVADO:
            livro.situacao = Livro.Situacao.DISPONIVEL
            livro.save(update_fields=["situacao"])

    messages.info(request, "Reserva cancelada.")
    if request.user == responsavel:
        return redirect("core:detalhes_livro", id=livro.pk)
    return redirect("core:meus_interesses")


@login_required
@require_POST
def marcar_nao_retirada(request: HttpRequest, id: int) -> HttpResponse:
    with transaction.atomic():
        reserva = get_object_or_404(
            Reserva.objects.select_for_update().select_related(
                "interesse", "interesse__livro", "interesse__livro__responsavel"
            ),
            pk=id,
        )
        livro = Livro.objects.select_for_update().get(pk=reserva.interesse.livro.pk)
        if livro.responsavel != request.user:
            raise PermissionDenied(
                "Você não tem permissão para informar a não retirada."
            )
        if reserva.status != Reserva.Status.APROVADA:
            messages.warning(request, "Esta reserva não está aguardando retirada.")
            return redirect("core:detalhes_livro", id=livro.pk)
        if (
            not reserva.data_retirada_prevista
            or timezone.localdate() <= reserva.data_retirada_prevista
        ):
            messages.warning(request, "A data prevista para retirada ainda não passou.")
            return redirect("core:detalhes_livro", id=livro.pk)

        reserva.status = Reserva.Status.NAO_RETIRADA
        reserva.data_encerramento = timezone.now()
        reserva.save(update_fields=["status", "data_encerramento"])
        livro.situacao = Livro.Situacao.DISPONIVEL
        livro.save(update_fields=["situacao"])

    messages.info(
        request,
        "A não retirada foi registrada. O livro está disponível novamente.",
    )
    return redirect("core:detalhes_livro", id=livro.pk)


@login_required
@require_POST
def iniciar_emprestimo(request: HttpRequest, id: int) -> HttpResponse:
    with transaction.atomic():
        reserva = get_object_or_404(
            Reserva.objects.select_for_update().select_related(
                "interesse",
                "interesse__livro",
                "interesse__livro__responsavel",
                "interesse__interessado",
            ),
            pk=id,
        )
        livro = Livro.objects.select_for_update().get(pk=reserva.interesse.livro.pk)
        if livro.responsavel != request.user:
            raise PermissionDenied(
                "Você não tem permissão para iniciar este empréstimo."
            )
        if reserva.status != Reserva.Status.APROVADA:
            messages.warning(request, "Esta reserva não está aprovada para retirada.")
            return redirect("core:detalhes_livro", id=livro.pk)
        if livro.situacao != Livro.Situacao.RESERVADO:
            messages.warning(request, "Este livro não está reservado.")
            return redirect("core:detalhes_livro", id=livro.pk)
        if Emprestimo.objects.filter(reserva=reserva).exists():
            messages.warning(request, "Esta reserva já possui um empréstimo.")
            return redirect("core:detalhes_livro", id=livro.pk)

        Emprestimo.objects.create(reserva=reserva)
        reserva.status = Reserva.Status.CONCLUIDA
        reserva.data_encerramento = timezone.now()
        reserva.save(update_fields=["status", "data_encerramento"])
        livro.situacao = Livro.Situacao.EMPRESTADO
        livro.save(update_fields=["situacao"])

    messages.success(request, "Empréstimo iniciado com sucesso.")
    return redirect("core:detalhes_livro", id=livro.pk)


@login_required
@require_POST
def devolver_livro(request: HttpRequest, id: int) -> HttpResponse:
    with transaction.atomic():
        emprestimo = get_object_or_404(
            Emprestimo.objects.select_for_update().select_related(
                "reserva",
                "reserva__interesse",
                "reserva__interesse__livro",
                "reserva__interesse__livro__responsavel",
            ),
            pk=id,
        )
        livro = Livro.objects.select_for_update().get(
            pk=emprestimo.reserva.interesse.livro.pk
        )
        if livro.responsavel != request.user:
            raise PermissionDenied(
                "Você não tem permissão para confirmar esta devolução."
            )
        if emprestimo.status != Emprestimo.Status.ATIVO:
            messages.warning(request, "Este empréstimo já foi encerrado.")
            return redirect("core:detalhes_livro", id=livro.pk)
        if livro.situacao != Livro.Situacao.EMPRESTADO:
            messages.warning(request, "Este livro não está marcado como emprestado.")
            return redirect("core:detalhes_livro", id=livro.pk)

        emprestimo.status = Emprestimo.Status.DEVOLVIDO
        emprestimo.devolvido_em = timezone.now()
        emprestimo.save(update_fields=["status", "devolvido_em"])
        livro.situacao = Livro.Situacao.DISPONIVEL
        livro.save(update_fields=["situacao"])

    messages.success(
        request,
        "Devolução registrada com sucesso. O livro está disponível novamente.",
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
        .prefetch_related(
            "reservas",
            "reservas__propostas",
            "reservas__cancelada_por",
            "reservas__emprestimo",
        )
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
            "titulo_erro": "Requisição inválida",
            "mensagem_erro": "Não foi possível processar a solicitação enviada.",
        },
        status=400,
    )


def erro_403(request: HttpRequest, exception) -> HttpResponse:
    return render(
        request,
        "core/erro.html",
        {
            "codigo_erro": "403",
            "titulo_erro": "Acesso não permitido",
            "mensagem_erro": "Você não possui permissão para realizar esta operação.",
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
            "mensagem_erro": "O conteúdo solicitado não foi encontrado ou não está disponível.",
        },
        status=404,
    )


def erro_500(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "core/erro.html",
        {
            "codigo_erro": "500",
            "titulo_erro": "Erro interno",
            "mensagem_erro": "Ocorreu um problema inesperado. Tente novamente em alguns instantes.",
        },
        status=500,
    )
