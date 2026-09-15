# esse módulo disponibiliza os recursos para criar modelos de banco de dados
from django.conf import settings
from django.db import models


class Livro(models.Model):
    class Situacao(models.TextChoices):
        DISPONIVEL = "DISPONIVEL", "Disponível"
        EMPRESTADO = "EMPRESTADO", "Emprestado"
        RESERVADO = "RESERVADO", "Reservado"

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
        ATIVA = "ATIVA", "Ativa"
        CANCELADA = "CANCELADA", "Cancelada"
        CONCLUIDA = "CONCLUIDA", "Concluída"

    interesse = models.ForeignKey(
        Interesse,
        on_delete=models.PROTECT,
        related_name="reservas",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ATIVA,
    )

    data_reserva = models.DateTimeField(auto_now_add=True)

    encerrada_em = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Reserva de {self.interesse.livro.titulo} para {self.interesse.interessado.username} - Status: {self.status}"
