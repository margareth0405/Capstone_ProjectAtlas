"""Application middleware kept thin by delegating to service objects."""

from library.services.usage import WebsiteUsageTracker


class WebsiteUsageMiddleware:
    """Update visit duration and page-view metadata after tracked responses."""

    tracker_class = WebsiteUsageTracker

    def __init__(self, get_response):
        self.get_response = get_response
        self.tracker = self.tracker_class()

    def __call__(self, request):
        response = self.get_response(request)
        is_heartbeat = getattr(request, "atlas_usage_heartbeat", False)
        content_type = response.get("Content-Type", "")
        is_page_view = (
            not is_heartbeat
            and request.method == "GET"
            and 200 <= response.status_code < 300
            and content_type.startswith("text/html")
        )
        self.tracker.track(request, page_view=is_page_view)
        return response
