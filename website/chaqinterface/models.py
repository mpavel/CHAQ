import datetime
from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Conversation(models.Model):
    user = models.ForeignKey(User, unique=True)
    question = models.CharField(max_length=250)
    answer = models.TextField()
    timestamp = models.DateTimeField('date published');

    def __unicode__(self):
        return 'Q: ' + self.question + ' A: ' + self.answer

    def was_created_today(self):
        return self.timestamp.date() == datetime.date.today()