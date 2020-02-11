from django.contrib import auth
from django.utils.translation import gettext_lazy as _
from rest_framework_json_api import serializers

from . import models


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
        fields = ('id', 'name', 'type', 'price', 'options')


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


class OrderSerializer(serializers.ModelSerializer):
    items = serializers.PrimaryKeyRelatedField(
        write_only=True,
        many=True,
        queryset=models.Item.objects.all(),
    )

    class Meta:
        model = models.Order
        fields = ('id', 'customer', 'items', 'notes', 'discount_code')
        read_only_fields = ('customer',)

    def validate_items(self, items):
        if len(items) == 0:
            raise serializers.ValidationError(_('Your order must include at least one item'))
        elif not any(item.type == models.Item.TYPES.PASS for item in items):
            raise serializers.ValidationError(_('Any order should include at least one pass'))

        return items

    def create(self, validated_data):
        items = validated_data.pop('items')
        order = models.Order.objects.create(**validated_data)

        for item in items:
            order.items.create(item=item, price=item.price)

        return order
