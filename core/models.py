# esse módulo disponibiliza os recursos para criar modelos de banco de dados
from django.conf import settings
from django.db import models


class Livro(models.Model):
    titulo = models.CharField(max_length=200)
    autor = models.CharField(max_length=150)
    genero = models.CharField(max_length=100)
    estado_conservacao = models.CharField(max_length=50)

    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='livros_disponibilizados',
    )
    
    descricao = models.TextField()


    def __str__(self) -> str:
        return self.titulo