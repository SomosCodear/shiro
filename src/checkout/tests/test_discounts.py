from django import urls
from rest_framework import test, status

from .. import factories


class DiscountCodeListTestCase(test.APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = urls.reverse('discountcode-list')
        cls.discount_codes = [
            factories.DiscountCodeFactory() for i in range(3)
        ]

    def test_returns_discount_code_by_code_filter(self):
        # act
        response = self.client.get(self.url, {'filter[code]': self.discount_codes[0].code})

        # assert
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.discount_codes[0].id)

    def test_returns_empty_queryset_if_no_code_filter(self):
        # act
        response = self.client.get(self.url)

        # assert
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
