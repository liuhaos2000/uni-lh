from django.db import models
from .base import BaseModel


class Todo(BaseModel):
    title = models.CharField(max_length=200)
    body = models.TextField()

    class Meta:
        db_table = 'todos_todo'

    def __str__(self):
        return self.title


class Tag(BaseModel):
    name = models.CharField(max_length=100)

    class Meta:
        db_table = 'todos_tag'

    def __str__(self):
        return self.name
