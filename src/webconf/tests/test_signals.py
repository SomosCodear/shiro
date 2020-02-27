import faker
import itertools
from django import test
from django.core import mail

from checkout import factories, models

fake = faker.Faker()


class SendPassEmailsTestCase(test.TestCase):
    def setUp(self):
        item = factories.ItemFactory(
            type=models.Item.TYPES.PASS,
            options=[
                factories.ItemOptionFactory.build(name='email', type=models.ItemOption.TYPES.EMAIL),
            ],
        )
        self.order = factories.OrderFactory(
            status=models.Order.STATUS.IN_PROCESS,
            items=[item, item],
        )
        for order_item in self.order.order_items.all():
            order_item.options.create(
                item_option=item.options.first(),
                value=fake.email(),
            )

    def test_should_send_email_to_pass_owners(self):
        # arrange
        self.order.status = models.Order.STATUS.PAID

        # act
        self.order.save()

        # assert
        passes = self.order.order_items.filter(item__type=models.Item.TYPES.PASS)
        self.assertEqual(len(mail.outbox), passes.count())

        sent_emails_addresses = list(itertools.chain.from_iterable(
            email.recipients() for email in mail.outbox
        ))
        passes_addresses = [
            order_item.options.get(item_option__name='email').value
            for order_item in self.order.order_items.all()
        ]
        self.assertEqual(sent_emails_addresses, passes_addresses)
