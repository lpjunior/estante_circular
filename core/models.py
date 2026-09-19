from django.conf import settings
from django.db import models


class Livro(models.Model):
    GENERO_LABELS = {  # noqa: RUF012
        "fantasia": "Fantasia",
        "ficcao": "Ficção",
        "romance": "Romance",
        "terror": "Terror",
        "suspense": "Suspense",
        "aventura": "Aventura",
        "biografia": "Biografia",
        "literatura_brasileira": "Literatura Brasileira",
        "outros": "Outros",
    }

    ESTADO_CONSERVACAO_LABELS = {  # noqa: RUF012
        "novo": "Novo",
        "muito_bom": "Muito bom",
        "bom": "Bom",
        "regular": "Regular",
    }

    class Situacao(models.TextChoices):
        DISPONIVEL = "DISPONIVEL", "Disponível"
        RESERVADO = "RESERVADO", "Reservado"
        EMPRESTADO = "EMPRESTADO", "Emprestado"

    titulo = models.CharField(max_length=200)
    autor = models.CharField(max_length=150)
    genero = models.CharField(max_length=100)
    estado_conservacao = models.CharField(max_length=50)
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="livros_disponibilizados",
    )
    descricao = models.TextField()
    ativo = models.BooleanField(default=True)
    situacao = models.CharField(
        max_length=20,
        choices=Situacao.choices,
        default=Situacao.DISPONIVEL,
    )

    @property
    def genero_display(self) -> str:
        return self.GENERO_LABELS.get(
            self.genero,
            self.genero.replace("_", " ").title(),
        )

    @property
    def estado_conservacao_display(self) -> str:
        return self.ESTADO_CONSERVACAO_LABELS.get(
            self.estado_conservacao,
            self.estado_conservacao.replace("_", " ").title(),
        )

    def __str__(self) -> str:
        return self.titulo


class Interesse(models.Model):
    class Status(models.TextChoices):
        PENDENTE = "PENDENTE", "Pendente"
        ACEITO = "ACEITO", "Aceito"
        RECUSADO = "RECUSADO", "Recusado"

    livro = models.ForeignKey(
        Livro,
        on_delete=models.PROTECT,
        related_name="interesses",
    )
    interessado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="interesses_em_livros",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE,
    )
    data_interesse = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [  # noqa: RUF012
            models.UniqueConstraint(
                fields=["livro", "interessado"],
                name="interesse_unico_por_livro_usuario",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.interessado.username} interessado em {self.livro.titulo}"


class Reserva(models.Model):
    class Status(models.TextChoices):
        AGUARDANDO_RESPONSAVEL = (
            "AGUARDANDO_RESPONSAVEL",
            "Aguardando responsável",
        )
        AGUARDANDO_INTERESSADO = (
            "AGUARDANDO_INTERESSADO",
            "Aguardando interessado",
        )
        APROVADA = "APROVADA", "Aprovada"
        CANCELADA = "CANCELADA", "Cancelada"
        NAO_RETIRADA = "NAO_RETIRADA", "Não retirada"
        CONCLUIDA = "CONCLUIDA", "Concluída"

    interesse = models.ForeignKey(
        Interesse,
        on_delete=models.PROTECT,
        related_name="reservas",
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.AGUARDANDO_RESPONSAVEL,
    )
    data_retirada_prevista = models.DateField(null=True, blank=True)
    data_reserva = models.DateTimeField(auto_now_add=True)
    data_aprovacao = models.DateTimeField(null=True, blank=True)
    data_encerramento = models.DateTimeField(null=True, blank=True)
    cancelada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reservas_canceladas",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-data_reserva"]  # noqa: RUF012

    def __str__(self) -> str:
        return (
            f"Reserva de {self.interesse.livro.titulo} para "
            f"{self.interesse.interessado.username} - {self.get_status_display()}" # type: ignore
        )


class PropostaReserva(models.Model):
    class Autor(models.TextChoices):
        INTERESSADO = "INTERESSADO", "Interessado"
        RESPONSAVEL = "RESPONSAVEL", "Responsável"

    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        related_name="propostas",
    )
    data_retirada = models.DateField()
    autor = models.CharField(max_length=20, choices=Autor.choices)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["criada_em"]  # noqa: RUF012

    def __str__(self) -> str:
        return (
            f"Proposta de {self.get_autor_display()} para " # type: ignore
            f"{self.data_retirada:%d/%m/%Y}"
        )


class Emprestimo(models.Model):
    class Status(models.TextChoices):
        ATIVO = "ATIVO", "Ativo"
        DEVOLVIDO = "DEVOLVIDO", "Devolvido"

    reserva = models.OneToOneField(
        Reserva,
        on_delete=models.PROTECT,
        related_name="emprestimo",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ATIVO,
    )
    emprestado_em = models.DateTimeField(auto_now_add=True)
    devolvido_em = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Empréstimo de {self.reserva.interesse.livro}"
