from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("jobs/start/", views.start_recording_job, name="start_recording_job"),
    path("jobs/<int:job_id>/status/", views.job_status, name="job_status"),
    path("jobs/<int:job_id>/stop/", views.stop_recording, name="stop_recording"),
    path("meeting/<str:stem>/", views.meeting_detail, name="meeting_detail"),
    path(
        "meeting/<str:stem>/download/",
        views.download_transcript,
        name="download_transcript",
    ),
    path(
        "meeting/<str:stem>/audio/<str:speaker_id>/",
        views.speaker_audio,
        name="speaker_audio",
    ),
    path(
        "meeting/<str:stem>/speaker/<str:speaker_id>/",
        views.speaker_edit,
        name="speaker_edit",
    ),
    path(
        "meeting/<str:stem>/jobs/start/",
        views.start_job,
        name="start_job",
    ),
    path(
        "meeting/<str:stem>/actions/",
        views.action_buttons,
        name="action_buttons",
    ),
]
