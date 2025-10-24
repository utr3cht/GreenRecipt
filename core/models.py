# core/models.py
from django.db import models


class Receipt(models.Model):
    image = models.ImageField(upload_to="receipts/%Y/%m/%d/")
    created_at = models.DateTimeField(auto_now_add=True)


class Inquiry(models.Model):
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
