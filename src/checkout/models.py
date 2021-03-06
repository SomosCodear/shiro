from django.conf import settings
from django.db import models
from django.core import validators, signing
from django.contrib.postgres import fields as postgres_fields
from model_utils import choices, fields as util_fields, tracker
from djmoney.models import fields as money_fields
from djmoney import money

from . import validators as custom_validators, signals


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

    def validate_value(self, value):
        if self.type == ItemOption.TYPES.EMAIL:
            validators.EmailValidator({
                'value': 'Debe ingresar un email válido',
            })(value)


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

    def calculate_discount(self, value):
        discount = money.Money(0, 'ARS')

        if self.fixed_value is not None:
            discount = self.fixed_value
        elif self.percentage is not None:
            discount = value * self.percentage / 100

        return discount

    def calculate_order_item_discount(self, order_item):
        discount = money.Money(0, 'ARS')

        if self.type == self.TYPES.ITEM and order_item.item in self.items.all():
            base_total = order_item.calculate_base_total()
            discount = self.calculate_discount(base_total)

        return discount

    def calculate_order_discount(self, order):
        discount = money.Money(0, 'ARS')

        if self.type == self.TYPES.ORDER:
            base_total = order.calculate_base_total()
            discount = self.calculate_discount(base_total)
        elif self.type == self.TYPES.ITEM:
            discount = sum(
                self.calculate_order_item_discount(order_item)
                for order_item in order.order_items.all()
            )

        return discount


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
    CUIT_LENGTH = 11

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='customer',
    )
    identity_document = models.CharField(max_length=50)
    company = models.CharField(max_length=100, null=True, blank=True)

    @staticmethod
    def generate_customer_token(email, identity_document):
        return signing.dumps((email, identity_document))

    @staticmethod
    def parse_customer_token(token):
        return signing.loads(token)

    def __str__(self):
        return str(self.user)

    def is_identity_document_cuit(self):
        return len(self.identity_document) == self.CUIT_LENGTH

    def generate_token(self):
        return Customer.generate_customer_token(self.user.email, self.identity_document)


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
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(null=True, blank=True)
    items = models.ManyToManyField('Item', through='OrderItem', related_name='orders')
    preference_id = models.CharField(max_length=100, null=True, blank=True)
    external_id = models.CharField(max_length=100, null=True, blank=True)
    status = util_fields.StatusField()

    status_tracker = tracker.FieldTracker(fields=['status'])

    def __str__(self):
        return f'Orden {self.id} ({self.customer})'

    def save(self, *args, **kwargs):
        order_paid = self.status_tracker.previous('status') != self.STATUS.PAID and \
            self.status == self.STATUS.PAID

        super().save(*args, **kwargs)

        if order_paid:
            signals.order_paid.send(sender=self.__class__, order=self)

    def calculate_base_total(self):
        return sum(order_item.calculate_base_total() for order_item in self.order_items.all())

    def calculate_discount(self):
        if self.discount_code:
            discount = self.discount_code.calculate_order_discount(self)
        else:
            discount = money.Money(0, 'ARS')

        return discount

    def calculate_total(self):
        total = self.calculate_base_total() - self.calculate_discount()

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

    def calculate_discount(self):
        if self.order.discount_code is not None:
            discount = self.order.discount_code.calculate_order_item_discount(self)
        else:
            discount = money.Money(0, 'ARS')

        return discount

    def calculate_total(self):
        total = self.calculate_base_total() - self.calculate_discount()

        return total


class OrderItemOption(models.Model):
    order_item = models.ForeignKey('OrderItem', on_delete=models.CASCADE, related_name='options')
    item_option = models.ForeignKey('ItemOption', on_delete=models.CASCADE, related_name='+')
    value = postgres_fields.JSONField(validators=[custom_validators.validate_single_value])

    class Meta:
        unique_together = ('order_item', 'item_option')

    def __str__(self):
        return f'{self.item_option}: {self.value}'

    def clean(self):
        self.item_option.validate_value(self.value)


class Invoice(models.Model):
    order = models.OneToOneField('Order', on_delete=models.CASCADE)
    number = models.PositiveIntegerField()
    cae = models.CharField(max_length=100)
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
