from django import forms

from core.models import Livro


class LivroForm(forms.ModelForm):
    GENEROS = [
        ("fantasia", "Fantasia"),
        ("ficcao", "Ficção"),
        ("romance", "Romance"),
        ("terror", "Terror"),
        ("suspense", "Suspense"),
        ("aventura", "Aventura"),
        ("biografia", "Biografia"),
        ("literatura_brasileira", "Literatura Brasileira"),
        ("outros", "Outros"),
    ]

    ESTADO_CONSERVACAO = [
        ("novo", "Novo"),
        ("muito_bom", "Muito Bom"),
        ("bom", "Bom"),
        ("regular", "Regular"),
    ]

    genero = forms.ChoiceField(choices=GENEROS, label="Gênero ou categoria")

    estado_conservacao = forms.ChoiceField(
        choices=ESTADO_CONSERVACAO, label="Estado de Conservação"
    )

    class Meta:
        model = Livro
        fields = ["titulo", "autor", "genero", "estado_conservacao", "descricao"]

        labels = {
            "titulo": "Título do livro",
            "autor": "Autor",
            "descricao": "Descrição do livro",
        }

        widgets = {
            "titulo": forms.TextInput(
                attrs={
                    "placeholder": "Ex.: O Hobbit",
                    "required": True,
                }
            ),
            "autor": forms.TextInput(
                attrs={
                    "placeholder": "Ex.: J.R.R. Tolkien",
                    "required": True,
                }
            ),
            "descricao": forms.Textarea(
                attrs={
                    "placeholder": "Ex.: Um livro sobre a Terra Média",
                    "required": True,
                    "rows": 6,
                }
            ),
        }

    def clean_titulo(self):
        titulo = self.cleaned_data.get("titulo")
        titulo = titulo.strip() if titulo else ""

        if not titulo:
            raise forms.ValidationError("O título é obrigatório.")
        return titulo

    def clean_autor(self):
        autor = self.cleaned_data.get("autor")
        autor = autor.strip() if autor else ""

        if len(autor) < 2:
            raise forms.ValidationError("O autor deve ter pelo menos 2 caracteres.")

        if not autor:
            raise forms.ValidationError("O autor é obrigatório.")
        return autor

    def clean_descricao(self):
        descricao = self.cleaned_data.get("descricao")
        descricao = descricao.strip() if descricao else ""

        if len(descricao) < 10:
            raise forms.ValidationError(
                "A descrição deve ter pelo menos 10 caracteres."
            )

        if not descricao:
            raise forms.ValidationError("A descrição é obrigatória.")
        return descricao
