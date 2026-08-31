"""Administrator AI Detection view."""

from django.views.generic import TemplateView

from library.forms import AIDetectionForm
from library.services.ai_detection import AIDetectionError, RobertaAIDetector
from library.services.documents import (
    DocumentExtractionError,
    DocumentTextExtractor,
)

from .mixins import PageContextMixin, StaffRequiredMixin


class StaffAIDetectionView(StaffRequiredMixin, PageContextMixin, TemplateView):
    """Analyze pasted text or text extracted from a supported document."""

    template_name = "library/admin/ai_detection.html"
    active_page = "ai_detection"
    form_class = AIDetectionForm
    analyzer_class = RobertaAIDetector
    extractor_class = DocumentTextExtractor

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("form", self.form_class())
        return context

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        context = self.get_context_data(form=form)
        if not form.is_valid():
            return self.render_to_response(context)

        text = form.cleaned_data.get("text")
        document = form.cleaned_data.get("document")
        source_label = "Pasted text"
        if document:
            try:
                text = self.extractor_class().extract(document)
            except DocumentExtractionError as error:
                form.add_error("document", str(error))
                return self.render_to_response(context)
            source_label = document.name

        try:
            context["detection_result"] = self.analyzer_class().analyze(text)
        except AIDetectionError as error:
            form.add_error(None, str(error))
            return self.render_to_response(context)
        context["detection_source"] = source_label
        return self.render_to_response(context)
