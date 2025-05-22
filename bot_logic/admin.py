from django.contrib import admin
from .models import (
    UserTg, Client, Speaker,
    Event, Session, SpeakerSession,
    Question
)


@admin.register(UserTg)
class UserTgAdmin(admin.ModelAdmin):
    list_display = ("tg_id", "nic_tg", "is_organizator")
    search_fields = ("tg_id", "nic_tg")
    list_filter = ("is_organizator",)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_phone", "stack", "favorite_stack")
    search_fields = ("name", "contact_phone")
    list_filter = ("stack", "favorite_stack")


@admin.register(Speaker)
class SpeakerAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_phone", "stack")
    search_fields = ("name", "contact_phone")
    list_filter = ("stack",)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "start_event", "finish_event")
    search_fields = ("name", "address")
    list_filter = ("start_event",)


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("title", "event", "start_session",
                    "finish_session", "address")
    search_fields = ("title", "event__name")
    list_filter = ("event",)


@admin.register(SpeakerSession)
class SpeakerSessionAdmin(admin.ModelAdmin):
    list_display = ("topic", "speaker", "session",
                    "start_session", "finish_session")
    search_fields = ("topic", "speaker__name", "session__title")
    list_filter = ("speaker",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("speaker", "client", "created_at")
    search_fields = ("text", "speaker__name", "client__name")
    list_filter = ("created_at",)
