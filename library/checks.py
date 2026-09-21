"""ATLAS-specific additions to Django's deployment check framework."""

from django.core.checks import Error, Tags, Warning, register

from library.services.deployment import DeploymentReadinessService


@register(Tags.security, deploy=True)
def production_configuration_checks(app_configs, **kwargs):
    """Report production settings that would break or weaken ATLAS."""

    messages = []
    for finding in DeploymentReadinessService().inspect_configuration():
        message_class = Error if finding.severity == "error" else Warning
        messages.append(
            message_class(
                finding.message,
                hint=finding.hint,
                id=finding.code,
            )
        )
    return messages
