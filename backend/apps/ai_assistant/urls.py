from django.urls import path

from . import views

urlpatterns = [
    path("analyze-prompt/", views.analyze_prompt, name="ai-analyze-prompt"),
    path("execute/", views.execute_partner_creation, name="ai-execute"),
    path("clarify/", views.clarification_response, name="ai-clarify"),
]
