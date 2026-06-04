from django.db import models


class SpeakerMapping(models.Model):
    meeting_stem = models.CharField(max_length=32)
    speaker_id = models.CharField(max_length=32)
    display_name = models.CharField(max_length=128)

    class Meta:
        unique_together = ["meeting_stem", "speaker_id"]

    def __str__(self) -> str:
        return f"{self.meeting_stem}/{self.speaker_id} -> {self.display_name}"


class Job(models.Model):
    class TaskType(models.TextChoices):
        RECORD = "record", "Record"
        TRANSCRIBE = "transcribe", "Transcribe"
        DIARIZE = "diarize", "Diarize"
        MERGE = "merge", "Merge"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    meeting_stem = models.CharField(max_length=32)
    task_type = models.CharField(max_length=16, choices=TaskType.choices)
    language = models.CharField(max_length=16, default='auto', blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"{self.meeting_stem}/{self.task_type} [{self.status}]"
