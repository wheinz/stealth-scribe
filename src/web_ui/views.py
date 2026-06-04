import threading
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
)
from django.shortcuts import render
from django.utils import timezone

from src.config import TIMEZONE

from .audio import extract_speaker_clip
from .meetings import (
    load_merged,
    scan_meetings,
    wav_path,
)
from .models import Job, SpeakerMapping

_tz = ZoneInfo(TIMEZONE) if TIMEZONE else None

_stop_events: dict[int, threading.Event] = {}
_merge_locks: dict[str, threading.Lock] = {}
_merge_lock_guard = threading.Lock()


def _get_merge_lock(stem: str) -> threading.Lock:
    with _merge_lock_guard:
        if stem not in _merge_locks:
            _merge_locks[stem] = threading.Lock()
        return _merge_locks[stem]


def _run_job(job_id: int) -> None:
    job = Job.objects.get(id=job_id)
    job.status = Job.Status.RUNNING
    job.started_at = timezone.now()
    job.save()

    task_type = job.task_type
    stem = job.meeting_stem

    try:
        from src.diarizer import diarize  # noqa: PLC0415
        from src.merger import merge  # noqa: PLC0415
        from src.recorder import record  # noqa: PLC0415
        from src.transcriber import transcribe  # noqa: PLC0415

        wav = Path(f"data/raw/meeting_{stem}/meeting_{stem}.wav")

        if task_type == Job.TaskType.RECORD:
            stop_event = _stop_events.get(job_id)
            output = record(stop_event=stop_event, output_path=wav)
            if output is None:
                raise RuntimeError("Recording failed — no microphone available")
        elif task_type == Job.TaskType.TRANSCRIBE:
            import socket
            import subprocess
            import time

            proc = subprocess.Popen(
                [
                    '/home/thomas/stealth-scribe/vendor/whisper.cpp/build/bin/whisper-server',
                    '-m', '/home/thomas/stealth-scribe/models/ggml-small.bin',
                    '--host', '0.0.0.0', '--port', '8080',
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                for _ in range(30):
                    time.sleep(1)
                    try:
                        with socket.create_connection(('127.0.0.1', 8080), timeout=1):
                            break
                    except (ConnectionRefusedError, OSError):
                        pass
                else:
                    raise RuntimeError('Whisper server failed to start within 30s')
                transcribe(wav, language=job.language)
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
        elif task_type == Job.TaskType.DIARIZE:
            diarize(wav)
        elif task_type == Job.TaskType.MERGE:
            merge(wav)

        job.status = Job.Status.COMPLETED
    except Exception as e:
        job.status = Job.Status.FAILED
        job.error = str(e)
    finally:
        job.finished_at = timezone.now()
        job.save()
        _stop_events.pop(job_id, None)

    if job.status != Job.Status.COMPLETED:
        return

    if task_type == Job.TaskType.DIARIZE:
        transcription_done = Job.objects.filter(
            meeting_stem=stem,
            task_type=Job.TaskType.TRANSCRIBE,
            status=Job.Status.COMPLETED,
        ).exists()

        if transcription_done:
            lock = _get_merge_lock(stem)
            with lock:
                merge_exists = Job.objects.filter(
                    meeting_stem=stem, task_type=Job.TaskType.MERGE
                ).exists()
                if not merge_exists:
                    merge_job = Job.objects.create(
                        meeting_stem=stem, task_type=Job.TaskType.MERGE
                    )
                    t = threading.Thread(
                        target=_run_job,
                        args=(merge_job.id,),
                        daemon=True,
                    )
                    t.start()


def index(request: HttpRequest) -> HttpResponse:
    meetings = scan_meetings()
    active_recording = Job.objects.filter(
        task_type=Job.TaskType.RECORD,
        status__in=[Job.Status.PENDING, Job.Status.RUNNING],
    ).first()
    return render(
        request,
        "index.html",
        {"meetings": meetings, "active_recording": active_recording},
    )


def meeting_detail(request: HttpRequest, stem: str) -> HttpResponse:
    try:
        segments = load_merged(stem)
    except FileNotFoundError:
        segments = None

    has_wav = wav_path(stem).exists()

    if not segments and not has_wav:
        return render(request, "meeting_detail.html", {"error": "wav", "stem": stem})

    if segments:
        mappings = {
            m.speaker_id: m.display_name
            for m in SpeakerMapping.objects.filter(meeting_stem=stem)
        }
        for seg in segments:
            sid = seg.get("speaker", "")
            seg["display_name"] = mappings.get(sid, "") if sid else ""

    jobs = {j.task_type: j for j in Job.objects.filter(meeting_stem=stem)}
    has_running_job = any(
        j.status in [Job.Status.PENDING, Job.Status.RUNNING] for j in jobs.values()
    )

    return render(
        request,
        "meeting_detail.html",
        {
            "stem": stem,
            "segments": segments,
            "has_wav": has_wav,
            "jobs": jobs,
            "has_running_job": has_running_job,
        },
    )


def download_transcript(request: HttpRequest, stem: str) -> HttpResponse:
    try:
        segments = load_merged(stem)
    except FileNotFoundError:
        raise Http404("Transcript not found")

    mappings = {
        m.speaker_id: m.display_name
        for m in SpeakerMapping.objects.filter(meeting_stem=stem)
    }

    lines = []
    for seg in segments:
        sid = seg.get("speaker", "")
        label = mappings.get(sid, sid)
        lines.append(f"{label}: {seg['text']}")

    text = "\n".join(lines) + "\n"

    response = HttpResponse(text, content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="meeting_{stem}_transcript.txt"'
    )
    return response


def speaker_audio(request: HttpRequest, stem: str, speaker_id: str) -> HttpResponse:
    try:
        segments = load_merged(stem)
    except FileNotFoundError:
        raise Http404("Meeting not found")

    clip = extract_speaker_clip(wav_path(stem), speaker_id, segments)
    if clip is None:
        raise Http404("Speaker not found in meeting")

    return HttpResponse(clip, content_type="audio/wav")


def speaker_edit(request: HttpRequest, stem: str, speaker_id: str) -> HttpResponse:
    if request.method == "POST":
        display_name = request.POST.get("display_name", "").strip()
        if not display_name:
            return HttpResponseBadRequest("Name is required")

        mapping, _ = SpeakerMapping.objects.update_or_create(
            meeting_stem=stem,
            speaker_id=speaker_id,
            defaults={"display_name": display_name},
        )

        return render(
            request,
            "partials/speaker_row.html",
            {
                "stem": stem,
                "speaker_id": speaker_id,
                "display_name": mapping.display_name,
            },
        )

    try:
        mapping = SpeakerMapping.objects.get(meeting_stem=stem, speaker_id=speaker_id)
        current_name = mapping.display_name
    except SpeakerMapping.DoesNotExist:
        current_name = ""

    return render(
        request,
        "partials/speaker_edit_form.html",
        {"stem": stem, "speaker_id": speaker_id, "current_name": current_name},
    )


def start_recording_job(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    stem = datetime.now(tz=_tz).strftime("%Y%m%d_%H%M%S")
    task_type = Job.TaskType.RECORD

    existing = Job.objects.filter(
        task_type=task_type,
        status__in=[Job.Status.PENDING, Job.Status.RUNNING],
    ).first()
    if existing:
        return render(request, "partials/job_status.html", {"job": existing})

    job = Job.objects.create(meeting_stem=stem, task_type=task_type)
    _stop_events[job.id] = threading.Event()

    t = threading.Thread(target=_run_job, args=(job.id,), daemon=True)
    t.start()

    return render(request, "partials/job_status.html", {"job": job, "stem": stem})


def start_job(request: HttpRequest, stem: str) -> HttpResponse:
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    task_type = request.POST.get("task_type", "").strip()
    if task_type not in Job.TaskType.values:
        return HttpResponseBadRequest(f"Invalid task_type: {task_type}")

    existing = Job.objects.filter(
        meeting_stem=stem,
        task_type=task_type,
        status__in=[Job.Status.PENDING, Job.Status.RUNNING],
    ).first()
    if existing:
        return _render_action_buttons(request, stem)

    language = request.POST.get("language", "auto").strip() or "auto"
    job = Job.objects.create(meeting_stem=stem, task_type=task_type, language=language)
    t = threading.Thread(target=_run_job, args=(job.id,), daemon=True)
    t.start()

    return _render_action_buttons(request, stem)


def action_buttons(request: HttpRequest, stem: str) -> HttpResponse:
    return _render_action_buttons(request, stem)


def _render_action_buttons(request: HttpRequest, stem: str) -> HttpResponse:
    jobs = _get_jobs_dict(stem)
    transcribe_job = jobs.get("transcribe")
    diarize_job = jobs.get("diarize")
    merge_job = jobs.get("merge")
    has_running = any(
        j.status in [Job.Status.PENDING, Job.Status.RUNNING]
        for j in [transcribe_job, diarize_job, merge_job]
        if j
    )
    return render(
        request,
        "partials/action_buttons.html",
        {
            "stem": stem,
            "has_wav": wav_path(stem).exists(),
            "transcribe_job": transcribe_job,
            "diarize_job": diarize_job,
            "merge_job": merge_job,
            "has_running_job": has_running,
        },
    )


def job_status(request: HttpRequest, job_id: int) -> HttpResponse:
    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        raise Http404("Job not found")

    stem = job.meeting_stem if job.task_type == Job.TaskType.RECORD else None
    return render(
        request,
        "partials/job_status.html",
        {"job": job, "stem": stem},
    )


def stop_recording(request: HttpRequest, job_id: int) -> HttpResponse:
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        raise Http404("Job not found")

    event = _stop_events.get(job_id)
    if event:
        event.set()

    return render(request, "partials/job_status.html", {"job": job})


def _get_jobs_dict(stem: str) -> dict[str, Job]:
    return {j.task_type: j for j in Job.objects.filter(meeting_stem=stem)}
