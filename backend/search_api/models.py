from django.db import models


class ProcessedURL(models.Model):
    url = models.URLField(max_length=500, unique=True)
    processed_at = models.DateTimeField(auto_now_add=True)
    chunks_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-processed_at']
    
    def __str__(self):
        return self.url

