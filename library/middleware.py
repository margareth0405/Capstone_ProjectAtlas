"""Application middleware kept thin by delegating to service objects."""

from library.services.usage import WebsiteUsageTracker


class WebsiteUsageMiddleware:
    """Track duration on requests and page views from browser navigation events."""

    tracker_class = WebsiteUsageTracker

    def __init__(self, get_response):
        self.get_response = get_response
        self.tracker = self.tracker_class()

    def __call__(self, request):
        response = self.get_response(request)
        page_path = getattr(request, "atlas_usage_page_path", "")
        self.tracker.track(
            request,
            page_view=bool(page_path),
            page_path=page_path,
        )
        return response
