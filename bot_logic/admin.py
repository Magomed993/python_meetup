from django.contrib import admin
from .models import (
    UserTg, Client, Speaker,
    Event, Session, SpeakerSession,
    Question
)


@admin.register(UserTg)
class UserTgAdmin(admin.ModelAdmin):
    list_display = ("tg_id", "nic_tg", "is_organizator", "is_speaker")
    search_fields = ("tg_id", "nic_tg")
    list_filter = ("is_organizator",)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_phone", "favorite_stack")
    search_fields = ("name", "contact_phone")
    list_filter = ("favorite_stack",)


@admin.register(Speaker)
class SpeakerAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_phone")
    search_fields = ("name", "contact_phone")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "start_event", "finish_event")
    search_fields = ("name", "address")
    list_filter = ("start_event",)


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("title", )
    search_fields = ("title", )
    list_filter = ("title",)


@admin.register(SpeakerSession)
class SpeakerSessionAdmin(admin.ModelAdmin):
    list_display = ("speaker", "session",
                    "start_session", "finish_session")
    search_fields = ("speaker__name", "session__title")
    list_filter = ("speaker",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("speaker", "client", "created_at")
    search_fields = ("text", "speaker__name", "client__name")
    list_filter = ("created_at",)
