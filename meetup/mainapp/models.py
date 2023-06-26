from django.db import models
from django.core import validators


USER_ROLE_CHOICES = [
    ("L", "Listener"),
    ("S", "Speaker"),
    ("O", "Organizer"),
]

class Event(models.Model):
    date = models.DateField()
    start_time = models.TimeField()
    event_name = models.CharField(max_length=50)
    place = models.CharField(max_length=50)
    active = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f'{self.event_name} {self.date}'


class User(models.Model):
    tg_id = models.CharField(max_length=30, unique=True)
    tg_nickname = models.CharField(max_length=30, blank=True)
    email = models.EmailField(
        max_length=254, blank=True,
        validators=[validators.EmailValidator(message="Invalid Email")])
    full_name = models.CharField(max_length=50, blank=True)
    workplace = models.CharField(max_length=150, blank=True)
    experience = models.TextField(blank=True)
    role = models.CharField(max_length=20, choices=USER_ROLE_CHOICES,
                            default='L')

    def __str__(self) -> str:
        if self.role == 'L':
            return f"Слушатель: {self.tg_nickname}"
        elif self.role == 'O':
            return f"Организатор: {self.tg_nickname}"
        elif self.role == 'S':
            if self.full_name:
                return f'{self.full_name}'
            return f'{self.tg_nickname}'


class Report(models.Model):
    report_title = models.CharField(max_length=50)
    planed_start_time = models.TimeField()
    planed_end_time = models.TimeField()
    actual_start_time = models.TimeField(blank=True, null=True)
    actual_end_time = models.TimeField(blank=True, null=True)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    speaker = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f'{self.report_title}'

    def is_report_over(self):
        if self.actual_end_time:
            return True
        return False


class Question(models.Model):
    question_title = models.CharField(max_length=150)
    question_text = models.TextField(unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    report = models.ForeignKey(Report, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f'{self.question_text[:25]}'
