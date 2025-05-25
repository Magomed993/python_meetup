from django.db import models

from django.db import models
from phonenumber_field.modelfields import PhoneNumberField


class UserTg(models.Model):
    tg_id = models.BigIntegerField("Телеграм id")
    nic_tg = models.CharField("Ник", max_length=50, null=True, blank=True)
    is_organizator = models.BooleanField("Организатор", default=False)
    is_speaker = models.BooleanField("Спикер", default=False)

    def __str__(self):
        return f"{self.tg_id}"

    class Meta:
        verbose_name = "пользователь"
        verbose_name_plural = "пользователи"


STACK_CHOICES = [
    ('backend', 'BACKEND'),
    ('frontend', 'FRONTEND'),
    ('full_stack', 'FULL STACK'),
]


class PersonBase(models.Model):
    """Для того, что не дублировать одинаковые поля"""

    user = models.ForeignKey(
        UserTg, on_delete=models.CASCADE, verbose_name="пользователь")
    name = models.CharField("Имя", max_length=50, null=True, blank=True)
    contact_phone = PhoneNumberField(
        "Мобильный номер", null=True, blank=True, unique=True, db_index=True)
    biography = models.TextField("О себе", null=True, blank=True)

    class Meta:
        abstract = True


class Client(PersonBase):
    favorite_stack = models.CharField(
        "Любимый стэк", max_length=15, choices=STACK_CHOICES, null=True, blank=True)
    is_registered = models.BooleanField("Зарегистрирован", default=False)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "клиент"
        verbose_name_plural = "клиенты"


class Speaker(PersonBase):

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "спикер"
        verbose_name_plural = "спикеры"


class Event(models.Model):
    name = models.CharField("Название", max_length=100, null=True)
    description = models.TextField("Описание", null=True)
    address = models.CharField(
        "Место проведения", max_length=100, null=True)
    start_event = models.DateTimeField("Время начала", null=True)
    finish_event = models.DateTimeField("Время завершения", null=True)
    # date = models.DateField("Дата", null=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "мероприятие"
        verbose_name_plural = "мероприятия"


class EventRegistration(models.Model):
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name='registrations')
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name='registrations')
    registration_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('client', 'event')
        verbose_name = 'регистрация на мероприятие'
        verbose_name_plural = 'регистрации на мероприятия'


class Session(models.Model):
    title = models.CharField(
        "Название", max_length=100, null=True, blank=True)
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="sessions",
        verbose_name="мероприятие", null=True
    )

    def __str__(self):
        return f"{self.title}"

    class Meta:
        verbose_name = "доклад"
        verbose_name_plural = "доклады"


class SpeakerSession(models.Model):
    session = models.ForeignKey(
        Session, on_delete=models.CASCADE,
        related_name="speaker_sessions", verbose_name="доклад")
    speaker = models.ForeignKey(
        Speaker, on_delete=models.CASCADE,
        related_name="speaker_sessions", verbose_name="спикер")
    start_session = models.DateTimeField("Начало выступления", null=True)
    finish_session = models.DateTimeField("Завершение", null=True)
    is_finish = models.BooleanField("Закончил ли выступление", default=False)

    def __str__(self):
        return f"{self.session.title}"

    class Meta:
        verbose_name = "выступление спикера"
        verbose_name_plural = "выступления спикеров"


class Question(models.Model):
    speaker = models.ForeignKey(
        Speaker, on_delete=models.CASCADE,
        related_name="questions", verbose_name="спикер")
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE,
        related_name="questions", verbose_name="клиент")
    text = models.TextField("Вопрос", null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE,
        related_name="questions", null=True, blank=True)

    def __str__(self):
        return f"Вопрос для {self.speaker.name} от  {self.client.name}"

    class Meta:
        verbose_name = "вопрос"
        verbose_name_plural = "вопросы"
