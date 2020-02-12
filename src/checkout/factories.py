import random
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
                self.options.add(option)
        else:
            for i in range(random.randint(1, 3)):
                ItemOptionFactory(item=self)


class ItemOptionFactory(factory.DjangoModelFactory):
    item = factory.SubFactory(ItemFactory)
    name = factory.Faker('word')
    type = factory.Faker('random_element', elements=[type[0] for type in models.ItemOption.TYPES])

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
