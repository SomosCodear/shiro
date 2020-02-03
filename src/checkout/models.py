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


class ItemOption(models.Model):
    TYPES = choices.Choices(('TEXT', 'Texto'), ('EMAIL', 'Email'), ('COLOR', 'Color'))

    item = models.ForeignKey('Item', on_delete=models.CASCADE, related_name='options')
    name = models.CharField(max_length=50)
    type = models.CharField(max_length=10, choices=TYPES)
    possible_values = postgres_fields.JSONField(
        null=True,
        validators=[custom_validators.validate_list],
    )

        blank=True,

class DiscountCode(models.Model):
    TYPES = choices.Choices(('ITEM', 'Item'), ('ORDER', 'Orden'))

    code = models.CharField(max_length=50)
    description = models.TextField()
    items = models.ManyToManyField('Item', related_name='discount_codes')
    type = models.CharField(max_length=10, choices=TYPES)
    percentage = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[validators.MaxValueValidator(100)],
    )
    fixed_value = models.PositiveIntegerField(null=True, blank=True)


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


class Customer(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    identity_document = models.CharField(max_length=50)
    company = models.CharField(max_length=100, null=True, blank=True)


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
    notes = models.TextField()


class OrderItem(models.Model):
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey('Item', on_delete=models.CASCADE, related_name='order_items')
    amount = models.PositiveSmallIntegerField(
        default=1,
        validators=[validators.MinValueValidator(1)],
    )
    price = money_fields.MoneyField(max_digits=7, decimal_places=2, default_currency='ARS')
    fulfilled = models.BooleanField(default=False)


class OrderItemOption(models.Model):
    order_item = models.ForeignKey('OrderItem', on_delete=models.CASCADE, related_name='options')
    item_option = models.ForeignKey('ItemOption', on_delete=models.CASCADE, related_name='+')
    value = postgres_fields.JSONField(validators=[custom_validators.validate_single_value])


class Invoice(models.Model):
    order = models.OneToOneField('Order', on_delete=models.CASCADE)
    number = models.PositiveIntegerField()
    file = models.FileField(upload_to='invoices/')


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


class CancellationItem(models.Model):
    cancellation = models.ForeignKey('Cancellation', on_delete=models.CASCADE, related_name='items')
    order_item = models.OneToOneField('OrderItem', on_delete=models.CASCADE, related_name='+')


class CreditNote(models.Model):
    cancellation = models.OneToOneField('Cancellation', on_delete=models.CASCADE)
    number = models.PositiveIntegerField()
    file = models.FileField(upload_to='credit_notes/')


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
