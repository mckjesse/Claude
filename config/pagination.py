from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """
    PageNumberPagination that honours the ``page_size`` query parameter
    so the frontend can request more (or fewer) results per page.

    Without this, DRF's built-in PageNumberPagination silently ignores
    ``?page_size=`` and always returns PAGE_SIZE results — which caused
    follow-up lists to appear incomplete when the frontend asked for 500
    and got 25.
    """

    page_size_query_param = "page_size"
    max_page_size = 500
