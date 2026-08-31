"""Application middleware kept thin by delegating to service objects."""

from library.services.usage import WebsiteUsageTracker


class WebsiteUsageMiddleware:
    """Persist only explicit visible-page events sent by the ATLAS browser UI."""

    tracker_class = WebsiteUsageTracker

    def __init__(self, get_response):
        self.get_response = get_response
        self.tracker = self.tracker_class()

    def __call__(self, request):
        response = self.get_response(request)
        event = getattr(request, "atlas_usage_event", "")
        if event:
            self.tracker.track(
                request,
                page_view=event == "page_view",
                page_path=getattr(request, "atlas_usage_page_path", ""),
            )
        return response