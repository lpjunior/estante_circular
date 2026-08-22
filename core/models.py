# esse módulo disponibiliza os recursos para criar modelos de banco de dados
from django.db import models


class Livro(models.Model):
    titulo = models.CharField(max_length=200)
    autor = models.CharField(max_length=150)
    genero = models.CharField(max_length=100)
    estado_conservacao = models.CharField(max_length=50)
    responsavel = models.CharField(max_length=150)
    descricao = models.TextField()


    def __str__(self) -> str:
        return self.titulo