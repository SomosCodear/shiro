import faker
from django import urls
from django.contrib import auth
from rest_framework import test, status

from user import factories as user_factories
from . import utils
from .. import models


class CustomerCreateTestCase(test.APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.fake = faker.Faker()
        cls.url = urls.reverse('customer-list')

    def test_should_create_customer(self):
        # arrange
        customer_data = {
            'email': self.fake.email(),
            'first_name': self.fake.first_name(),
            'identity_document': self.fake.numerify(text='########'),
        }
        payload = utils.build_json_api_payload('customer', customer_data)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            response.data.items() >= customer_data.items(),
            'Customer data not present in response',
        )
        self.assertTrue(
            models.Customer.objects.filter(
                identity_document=customer_data['identity_document'],
            ).exists(),
            'Customer was created successfully',
        )

    def test_should_create_user(self):
        # arrange
        customer_data = {
            'email': self.fake.email(),
            'first_name': self.fake.first_name(),
            'identity_document': self.fake.numerify(text='########'),
        }
        payload = utils.build_json_api_payload('customer', customer_data)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            auth.get_user_model().objects.filter(email=customer_data['email']).exists(),
            'User was created successfully',
        )

    def test_can_optionally_add_a_company(self):
        # arrange
        customer_data = {
            'email': self.fake.email(),
            'first_name': self.fake.first_name(),
            'identity_document': self.fake.numerify(text='########'),
            'company': self.fake.company(),
        }
        payload = utils.build_json_api_payload('customer', customer_data)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            response.data.items() >= customer_data.items(),
            'Customer data not present in response',
        )

    def test_should_validate_if_user_with_email_already_exists(self):
        # arrange
        user = user_factories.UserFactory()
        customer_data = {
            'email': user.email,
            'first_name': self.fake.first_name(),
            'identity_document': self.fake.numerify(text='########'),
        }
        payload = utils.build_json_api_payload('customer', customer_data)

        # act
        response = self.client.post(self.url, payload)

        # assert
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data[0]['source']['pointer'], '/data/attributes/email')
