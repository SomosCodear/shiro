import factory

from user import factories as user_factories
from . import models


class ItemFactory(factory.DjangoModelFactory):
    name = factory.Faker('word')
    type = factory.Faker('random_element', elements=[type[0] for type in models.Item.TYPES])
    price = factory.Faker('numerify', text='###.##')
    stock = factory.Faker('random_digit')

    class Meta:
        model = models.Item

    @factory.post_generation
    def options(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for option in extracted:
                option.item = self
                option.save()


class ItemOptionFactory(factory.DjangoModelFactory):
    name = factory.Faker('word')
    type = models.ItemOption.TYPES.TEXT

    class Meta:
        model = models.ItemOption


class CustomerFactory(factory.DjangoModelFactory):
    user = factory.SubFactory(user_factories.UserFactory)
    identity_document = factory.Faker('random_number', digits=8)

    class Meta:
        model = models.Customer


class DiscountCodeFactory(factory.DjangoModelFactory):
    code = factory.Faker('lexify', text='??????')
    description = factory.Faker('paragraph')
    type = models.DiscountCode.TYPES.ORDER
    percentage = factory.Faker('random_int', min=5, max=50)

    class Meta:
        model = models.DiscountCode

    @factory.post_generation
    def items(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for item in extracted:
                self.items.add(item)


class OrderFactory(factory.DjangoModelFactory):
    customer = factory.SubFactory(CustomerFactory)
    notes = factory.Faker('paragraph')

    class Meta:
        model = models.Order

    @factory.post_generation
    def items(self, create, extracted, **kwargs):
        if not create:
            return

        if not extracted:
            extracted = [ItemFactory() for i in range(3)]

        for item in extracted:
            OrderItemFactory(order=self, item=item)


class OrderItemFactory(factory.DjangoModelFactory):
    order = factory.SubFactory(OrderFactory)
    item = factory.SubFactory(ItemFactory)
    price = factory.SelfAttribute('item.price')

    class Meta:
        model = models.OrderItem


class OrderItemOptionFactory(factory.DjangoModelFactory):
    order_item = factory.SubFactory(OrderItemFactory)
    item_option = factory.SubFactory(ItemOptionFactory)
    value = factory.Faker('word')

    class Meta:
        model = models.OrderItemOption
