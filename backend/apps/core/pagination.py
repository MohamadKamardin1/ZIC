from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from collections import OrderedDict


class StandardPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'per_page'
    max_page_size = 1000

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('success', True),
            ('status_code', 200),
            ('message', 'Data retrieved successfully'),
            ('data', data),
            ('pagination', OrderedDict([
                ('page', self.page.number),
                ('per_page', self.get_page_size(self.request)),
                ('total', self.page.paginator.count),
                ('pages', self.page.paginator.num_pages),
            ])),
            ('meta', OrderedDict([
                ('timestamp', __import__('datetime').datetime.now().isoformat() + 'Z'),
                ('request_id', getattr(self.request, 'request_id', None)),
                ('version', 'v1'),
            ])),
        ]))
