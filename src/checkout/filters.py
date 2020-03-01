import django_filters
from django import forms
from . import models


class DiscountCodeFilterSetForm(forms.Form):
    def clean_code(self):
        code = self.cleaned_data['code']

        if not code:
            raise forms.ValidationError('The \'code\' filter must be present')

        return code

class DiscountCodeFilterSet(django_filters.FilterSet):
    class Meta:
        model = models.DiscountCode
        fields = ('code',)
        form = DiscountCodeFilterSetForm
