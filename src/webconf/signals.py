import templated_email
from django import dispatch
from checkout import models, signals as checkout_signals


@dispatch.receiver(checkout_signals.order_paid, dispatch_uid='webconf_send_pass_emails')
def send_pass_emails(sender, order=None, **kwargs):
    for order_item in order.order_items.filter(item__type=models.Item.TYPES.PASS):
        email = order_item.options.get(item_option__name='email').value
        templated_email.send_templated_mail(
            template_name='pass_paid',
            from_email='no-reply@webconf.tech',
            recipient_list=[email],
            context={
                'email': email,
            },
        )
