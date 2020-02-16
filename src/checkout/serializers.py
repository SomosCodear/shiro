import json
from django.contrib import auth
from django.utils.translation import gettext_lazy as _
from rest_framework_json_api import serializers, relations
from djmoney.contrib import django_rest_framework as djmoney_serializers

from . import models


class WritableResourceRelatedField(relations.ResourceRelatedField):
    def __init__(self, **kwargs):
        self.write_serializer = kwargs.pop('write_serializer', None)
        assert self.write_serializer is not None, (
            'WritableResourceRelatedField must provide a write_searializer'
        )

        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except ValueError:
                # show a useful error if they send a `pk` instead of resource object
                self.fail('incorrect_type', data_type=type(data).__name__)
        if not isinstance(data, dict):
            self.fail('incorrect_type', data_type=type(data).__name__)

        expected_relation_type = relations.get_resource_type_from_queryset(self.get_queryset())
        serializer_resource_type = self.get_resource_type_from_included_serializer()

        if serializer_resource_type is not None:
            expected_relation_type = serializer_resource_type

        if 'type' not in data:
            self.fail('missing_type')

        if data['type'] != expected_relation_type:
            self.conflict(
                'incorrect_relation_type',
                relation_type=expected_relation_type,
                received_type=data['type'],
            )

        write_representation = self.write_serializer.run_validation(data.get('attributes'))

        return write_representation


class ItemOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ItemOption
        fields = ('id', 'name', 'type')


class ItemSerializer(serializers.ModelSerializer):
    included_serializers = {
        'options': ItemOptionSerializer,
    }

    class Meta:
        model = models.Item
        fields = ('id', 'name', 'image', 'type', 'price', 'options')


class CustomerSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')

    class Meta:
        model = models.Customer
        fields = ('id', 'email', 'first_name', 'last_name', 'identity_document', 'company')

    def create(self, validated_data):
        User = auth.get_user_model()
        user_data = validated_data.pop('user')
        email = user_data.pop('email')
        user = User.objects.create_user(email, **user_data)

        customer = models.Customer.objects.create(user=user, **validated_data)

        return customer


class OrderItemOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.OrderItemOption
        fields = ('id', 'item_option', 'value')


class OrderItemSerializer(serializers.ModelSerializer):
    total = djmoney_serializers.MoneyField(14, 2, source='calculate_total', read_only=True)
    options = WritableResourceRelatedField(
        write_serializer=OrderItemOptionSerializer(),
        queryset=models.OrderItemOption.objects.none(),
        many=True,
        required=False,
    )

    included_serializers = {
        'item': ItemSerializer,
    }

    class Meta:
        model = models.OrderItem
        fields = ('id', 'item', 'amount', 'price', 'options', 'total')
        read_only_fields = ('price',)


class OrderSerializer(serializers.ModelSerializer):
    total = djmoney_serializers.MoneyField(14, 2, source='calculate_total', read_only=True)
    order_items = WritableResourceRelatedField(
        write_serializer=OrderItemSerializer(),
        queryset=models.OrderItem.objects.none(),
        many=True,
    )

    included_serializers = {
        'order_items': OrderItemSerializer,
    }

    class Meta:
        model = models.Order
        fields = ('id', 'customer', 'order_items', 'notes', 'discount_code', 'total')
        read_only_fields = ('customer',)

    def validate_order_items(self, order_items):
        if len(order_items) == 0:
            raise serializers.ValidationError(_('Your order must include at least one item'))
        elif not any(
            order_item['item'].type == models.Item.TYPES.PASS for order_item in order_items
        ):
            raise serializers.ValidationError(_('Any order should include at least one pass'))

        for order_item in order_items:
            item_options = set(order_item['item'].options.values_list('id', flat=True))
            received_options = set(
                order_item_option['item_option'].id
                for order_item_option in order_item.get('options', [])
            )

            if item_options != received_options:
                raise serializers.ValidationError(_('You must include all item options'))

        return order_items

    def create(self, validated_data):
        order_items = validated_data.pop('order_items')
        order = models.Order.objects.create(**validated_data)

        for order_item_data in order_items:
            options = order_item_data.pop('options', [])
            order_item = order.order_items.create(**order_item_data)

            for option_data in options:
                order_item.options.create(**option_data)

        return order
