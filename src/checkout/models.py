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
    image = models.ImageField(upload_to='image/items/', null=True)
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

    def calculate_discounted_total(self, total):
        if self.fixed_value is not None:
            total -= self.fixed_value
        elif self.percentage is not None:
            total -= total * self.percentage / 100

        return total

    def calculate_order_item_discounted_total(self, order_item):
        total = order_item.calculate_base_total()

        if self.type == self.TYPES.ITEM and order_item.item in self.items.all():
            total = self.calculate_discounted_total(total)

        return total

    def calculate_order_discounted_total(self, order):
        if self.type == self.TYPES.ORDER:
            base_total = order.calculate_base_total()
            total = self.calculate_discounted_total(base_total)
        elif self.type == self.TYPES.ITEM:
            total = sum(
                self.calculate_order_item_discounted_total(order_item)
                for order_item in order.order_items.all()
            )

        return total


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
    IDENTITY_DOCUMENT_TYPES = choices.Choices(
        ('DNI', 'DNI'),
        ('PSP', 'Pasaporte'),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    identity_document_type = models.CharField(max_length=3, choices=IDENTITY_DOCUMENT_TYPES)
    identity_document = models.CharField(max_length=50)
    company = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return str(self.user)


class Order(models.Model):
    STATUS = choices.Choices(
        ('CREATED', 'Creado'),
        ('IN_PROCESS', 'En proceso'),
        ('PAID', 'Pagado'),
        ('CANCELLED', 'Cancelado'),
    )

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
    items = models.ManyToManyField('Item', through='OrderItem', related_name='orders')
    preference_id = models.CharField(max_length=100, null=True, blank=True)
    external_id = models.CharField(max_length=100, null=True, blank=True)
    status = util_fields.StatusField()

    def __str__(self):
        return f'Orden {self.id} ({self.customer})'

    def calculate_base_total(self):
        return sum(order_item.calculate_base_total() for order_item in self.order_items.all())

    def calculate_total(self):
        if self.discount_code is None:
            total = self.calculate_base_total()
        else:
            total = self.discount_code.calculate_order_discounted_total(self)

        return total


class OrderItem(models.Model):
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='order_items')
    item = models.ForeignKey('Item', on_delete=models.CASCADE, related_name='order_items')
    price = money_fields.MoneyField(max_digits=7, decimal_places=2, default_currency='ARS')
    amount = models.PositiveIntegerField(default=1)
    fulfilled = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.amount} {self.item} ({self.price})'

    def save(self, *args, **kwargs):
        if self.id is None:
            self.price = self.item.price if self.item is not None else None

        super().save(*args, **kwargs)

    def calculate_base_total(self):
        return self.price * self.amount

    def calculate_total(self):
        if self.order.discount_code is None:
            total = self.calculate_base_total()
        else:
            total = self.order.discount_code.calculate_order_item_discounted_total(self)

        return total


class OrderItemOption(models.Model):
    order_item = models.ForeignKey('OrderItem', on_delete=models.CASCADE, related_name='options')
    item_option = models.ForeignKey('ItemOption', on_delete=models.CASCADE, related_name='+')
    value = postgres_fields.JSONField(validators=[custom_validators.validate_single_value])

    class Meta:
        unique_together = ('order_item', 'item_option')

    def __str__(self):
        return f'{self.item_option}: {self.value}'


class Invoice(models.Model):
    order = models.OneToOneField('Order', on_delete=models.CASCADE)
    number = models.PositiveIntegerField()
    file = models.FileField(upload_to='documents/invoices/')

    def __str__(self):
        return f'Factura {self.number} de {self.order}'


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
    file = models.FileField(upload_to='documents/credit_notes/')

    def __str__(self):
        return f'Nota de crédito de {self.cancellation.order}'
