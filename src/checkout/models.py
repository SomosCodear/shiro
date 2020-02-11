from django.conf import settings
from django.db import models
from django.contrib.postgres import fields as postgres_fields
from django.core import validators
from model_utils import choices, fields as util_fields
from djmoney.models import fields as money_fields
from . import validators as custom_validators


class Item(models.Model):
    TYPES = choices.Choices(('PASS', 'Pase'), ('ADDON', 'Addon'))

    name = models.CharField(max_length=200)
    type = models.CharField(max_length=10, choices=TYPES)
    price = money_fields.MoneyField(max_digits=7, decimal_places=2, default_currency='ARS')
    stock = models.PositiveIntegerField(default=0)
    cancellable = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ItemOption(models.Model):
    TYPES = choices.Choices(('TEXT', 'Texto'), ('EMAIL', 'Email'), ('COLOR', 'Color'))

    item = models.ForeignKey('Item', on_delete=models.CASCADE, related_name='options')
    name = models.CharField(max_length=50)
    type = models.CharField(max_length=10, choices=TYPES)
    possible_values = postgres_fields.JSONField(
        null=True,
        blank=True,
        validators=[custom_validators.validate_list],
    )

    def __str__(self):
        return f'{self.item} option: {self.name}'


class DiscountCode(models.Model):
    TYPES = choices.Choices(('ITEM', 'Item'), ('ORDER', 'Orden'))

    code = models.CharField(max_length=50)
    description = models.TextField()
    items = models.ManyToManyField('Item', related_name='discount_codes')
    type = models.CharField(max_length=10, choices=TYPES)
    percentage = models.PositiveIntegerField(
        null=True,
        validators=[validators.MaxValueValidator(100)],
    )
    fixed_value = money_fields.MoneyField(
        max_digits=7,
        decimal_places=2,
        default_currency='ARS',
        null=True,
    )

    def __str__(self):
        return f'{self.code} ({self.description})'


class DiscountCodeRestriction(models.Model):
    TYPES = choices.Choices(
        ('DATE', 'Fecha'),
        ('STOCK', 'Cantidad'),
        ('EMAIL', 'Email'),
        ('DOMAIN', 'Dominio'),
    )

    discount_code = models.ForeignKey(
        'DiscountCode',
        on_delete=models.CASCADE,
        related_name='restrictions',
    )
    type = models.CharField(max_length=10, choices=TYPES)
    value = postgres_fields.JSONField(validators=[custom_validators.validate_single_value])

    def __str__(self):
        return f'{self.type} restriction for {self.discount_code}'


class Customer(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    identity_document = models.CharField(max_length=50)
    company = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return str(self.user)


class Order(models.Model):
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='orders')
    discount_code = models.ForeignKey(
        'DiscountCode',
        on_delete=models.SET_NULL,
        related_name='orders',
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f'Orden {self.id} ({self.customer})'

    def calculate_total(self):
        total = sum(item.price for item in self.items.all())

        if self.discount_code is not None:
            if self.discount_code.fixed_value is not None:
                total -= self.discount_code.fixed_value
            elif self.discount_code.percentage is not None:
                total -= total * self.discount_code.percentage / 100

        return total


class OrderItem(models.Model):
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey('Item', on_delete=models.CASCADE, related_name='order_items')
    price = money_fields.MoneyField(max_digits=7, decimal_places=2, default_currency='ARS')
    fulfilled = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.item} ({self.price})'


class OrderItemOption(models.Model):
    order_item = models.ForeignKey('OrderItem', on_delete=models.CASCADE, related_name='options')
    item_option = models.ForeignKey('ItemOption', on_delete=models.CASCADE, related_name='+')
    value = postgres_fields.JSONField(validators=[custom_validators.validate_single_value])

    def __str__(self):
        return f'{self.item_option}: {self.value}'


class Invoice(models.Model):
    order = models.OneToOneField('Order', on_delete=models.CASCADE)
    number = models.PositiveIntegerField()
    file = models.FileField(upload_to='invoices/')

    def __str__(self):
        return f'Factura {self.number} de {self.order}'


class Payment(models.Model):
    STATUS = choices.Choices(
        ('CREATED', 'Creado'),
        ('IN_PROCESS', 'En proceso'),
        ('REJECTED', 'Rechazado'),
        ('APPROVED', 'Aprobado'),
        ('CANCELLED', 'Cancelado'),
    )

    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='payments')
    external_id = models.CharField(max_length=100)
    status = util_fields.StatusField()
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Pago {self.external_id} de {self.order}'


class Cancellation(models.Model):
    order = models.OneToOneField('Order', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    reason = models.TextField()
    cancelled_items = models.ManyToManyField(
        'OrderItem',
        related_name='cancellation',
        through='CancellationItem',
    )

    def __str__(self):
        return f'Cancelación de {self.order}'


class CancellationItem(models.Model):
    cancellation = models.ForeignKey('Cancellation', on_delete=models.CASCADE, related_name='items')
    order_item = models.OneToOneField('OrderItem', on_delete=models.CASCADE, related_name='+')

    def __str__(self):
        return f'Cancelación de {self.order_item}'


class CreditNote(models.Model):
    cancellation = models.OneToOneField('Cancellation', on_delete=models.CASCADE)
    number = models.PositiveIntegerField()
    file = models.FileField(upload_to='credit_notes/')

    def __str__(self):
        return f'Nota de crédito de {self.cancellation.order}'


class Refund(models.Model):
    STATUS = choices.Choices(
        ('CREATED', 'Creado'),
        ('COMPLETED', 'Completado'),
    )

    cancellation = models.OneToOneField('Cancellation', on_delete=models.CASCADE)
    external_id = models.CharField(max_length=100)
    status = util_fields.StatusField()
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return 'Refund de {self.cancellation.order}'
