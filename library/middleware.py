"""Application middleware kept thin by delegating to service objects."""

from library.services.usage import WebsiteUsageTracker


class WebsiteUsageMiddleware:
    """Update visit activity after each tracked application response."""

    tracker_class = WebsiteUsageTracker

    def __init__(self, get_response):
        self.get_response = get_response
        self.tracker = self.tracker_class()

    def __call__(self, request):
        response = self.get_response(request)
        self.tracker.track(request)
        return response
