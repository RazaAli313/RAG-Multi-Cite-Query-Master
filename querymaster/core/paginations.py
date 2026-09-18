from rest_framework import pagination


class PageNumberPagination(pagination.PageNumberPagination):
    page_size = 10
    max_page_size = 100
    page_size_query_param = "page_size"


class NoPagination(pagination.PageNumberPagination):
    page_size = None
    max_page_size = None
    page_size_query_param = None

    def paginate_queryset(self, queryset, request, view=None):
        self.page_size = queryset.count() or 1  # To make response consistent
        return super().paginate_queryset(queryset, request, view)
