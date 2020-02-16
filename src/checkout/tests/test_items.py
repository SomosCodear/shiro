import json
from django import urls
from rest_framework import test, status

from .. import factories


class ItemRetrieveTestCase(test.APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.items = [factories.ItemFactory() for i in range(10)]

    def test_should_return_all_items(self):
        # arrange
        expected_data = [
            {
                'id': item.id,
                'name': item.name,
                'type': item.type,
                'price': str(item.price.amount),
                'image': None,
                'options': [
                    {
                        'type': 'item-option',
                        'id': str(option.id),
                    } for option in item.options.all()
                ],
            } for item in self.items
        ]
        url = urls.reverse('item-list')

        # act
        response = self.client.get(url)

        # assert
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'], expected_data)

    def test_should_return_an_item_by_id(self):
        # arrange
        item = self.items[4]
        expected_data = {
            'id': item.id,
            'name': item.name,
            'type': item.type,
            'price': str(item.price.amount),
            'image': None,
            'options': [
                {
                    'type': 'item-option',
                    'id': str(option.id),
                } for option in item.options.all()
            ],
        }
        url = urls.reverse('item-detail', kwargs={'pk': item.id})

        # act
        response = self.client.get(url)

        # assert
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, expected_data)

    def test_should_include_item_options(self):
        # arrange
        item = self.items[5]
        expected_data = [
            {
                'type': 'item-option',
                'id': str(option.id),
                'attributes': {
                    'name': option.name,
                    'type': option.type,
                },
            } for option in item.options.all()
        ]
        url = urls.reverse('item-detail', kwargs={'pk': item.id})

        # act
        response = self.client.get(f'{url}?include=options')

        # assert
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content)['included'], expected_data)
