"""Administrator AI Detection view."""

from django.views.generic import TemplateView

from library.forms import AIDetectionForm
from library.services.ai_detection import WritingPatternAnalyzer

from .mixins import PageContextMixin, StaffRequiredMixin


class StaffAIDetectionView(StaffRequiredMixin, PageContextMixin, TemplateView):
    """Validate text input and present explainable writing-pattern metrics."""

    template_name = "library/admin/ai_detection.html"
    active_page = "ai_detection"
    form_class = AIDetectionForm
    analyzer_class = WritingPatternAnalyzer

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("form", self.form_class())
        return context

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        context = self.get_context_data(form=form)
        if form.is_valid():
            context["detection_result"] = self.analyzer_class().analyze(
                form.cleaned_data["text"]
            )
        return self.render_to_response(context)
