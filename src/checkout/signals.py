import django.dispatch

order_paid = django.dispatch.Signal(providing_args=['order'])
