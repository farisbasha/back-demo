import uuid
from django.utils import timezone
from django.db import models
from django.conf import settings

from django.contrib.auth.models import AbstractUser






class CustomUser(AbstractUser):
    class USER_ROLES(models.TextChoices):
        PART_TIME = 'parttime', _('Part-Time')
        FULL_TIME = 'fulltime', _('Full-Time')
        ADMIN = 'admin', _('Admin')
        TUTOR = 'tutor', _('Tutor')
    
    
    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True,
    )
    role = models.CharField(max_length=20, choices=USER_ROLES.choices,default=USER_ROLES.TUTOR)
    

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username','first_name','role']

    def __str__(self):
        return self.email
    class Meta:
        ordering = ['-date_joined']
        
        








class Tutor(models.Model):
    class USER_TYPES(models.TextChoices):
        PART_TIME = 'parttime', 'Part-Time'
        FULL_TIME = 'fulltime', 'Full-Time'
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    ref_id = models.CharField(max_length=100)
    email = models.EmailField(max_length=100)
    name = models.CharField(max_length=100)
    user_type = models.CharField(max_length=20, choices=USER_TYPES.choices)


    def __str__(self):
        return self.name

class Level(models.Model):
    class COURSE_TYPES(models.TextChoices):
        PART_TIME = 'parttime', 'Part-Time'
        FULL_TIME = 'fulltime', 'Full-Time'
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)
    type = models.CharField(max_length=20, choices=COURSE_TYPES.choices, default=COURSE_TYPES.PART_TIME)
    expire_duration_days = models.PositiveIntegerField(default=30)  # Default 30 days

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['order','type']

class Video(models.Model):
    
    class QUIZ_PASS_PERCENTAGE(models.IntegerChoices):
        ZERO = 0
        TENTH = 10
        TWENTY = 20
        THIRTY = 30
        FOURTY = 40
        FIFTY = 50
        SIXTY = 60
        SEVENTY = 70
        EIGHTY = 80
        NINETY = 90
        HUNDRED = 100
    
    level = models.ForeignKey(Level, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    video_link_low = models.URLField()
    video_link_high = models.URLField()
    thumbnail_image = models.URLField()
    order = models.PositiveIntegerField(default=0)
    notes_link = models.URLField(blank=True,null=True)
    quiz_pass_percentage = models.IntegerField(choices=QUIZ_PASS_PERCENTAGE.choices, default=QUIZ_PASS_PERCENTAGE.FIFTY)
   

    class Meta:
        ordering = ['level__order',]

    def __str__(self):
        return self.title



class Question(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='questions')
    question_text = models.CharField(max_length=500)
    option_a = models.CharField(max_length=200)
    option_b = models.CharField(max_length=200)
    option_c = models.CharField(max_length=200,null=True,blank=True)
    option_d = models.CharField(max_length=200,null=True,blank=True)
    correct_option = models.CharField(max_length=1, choices=[('a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D')])

    def __str__(self):
        return self.question_text
    


class TutorLevelProgress(models.Model):
    class STATUS_CHOICES(models.TextChoices):
        NOT_STARTED = 'not_started', 'Not Started'
        STARTED = 'started', 'Started'
        EXPIRED = 'expired', 'Expired'
        COMPLETED = 'completed', 'Completed'
        

    tutor = models.ForeignKey(Tutor, on_delete=models.CASCADE)
    level = models.ForeignKey(Level, on_delete=models.CASCADE)
    is_visible = models.BooleanField(default=True)
    expiration_date = models.DateTimeField(null=True, blank=True) 
    status = models.CharField(max_length=20, choices=STATUS_CHOICES.choices, default=STATUS_CHOICES.NOT_STARTED)
    
    


    def __str__(self):
        return f"{self.tutor.name} - {self.level.name} Progress"
    

class TutorVideoProgress(models.Model):
    
    class STATUS_CHOICES(models.TextChoices):
        NOT_STARTED = 'not_started', 'Not Started'
        STARTED = 'started', 'Started'
        COMPLETED = 'completed', 'Completed'
    
    tutor = models.ForeignKey(Tutor, on_delete=models.CASCADE)
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    current_time = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES.choices, default=STATUS_CHOICES.NOT_STARTED)
    quiz_percentage = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['tutor', 'video']

    def __str__(self):
        return f"{self.tutor.name} - {self.video.title} Progress"
    

class RenewalRequest(models.Model):
    tutor = models.ForeignKey(Tutor, on_delete=models.CASCADE)
    level = models.ForeignKey(Level, on_delete=models.CASCADE)
    request_date = models.DateTimeField(default=timezone.now)
    expired_date = models.DateTimeField()
    is_accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Renewal Request for {self.level} by {self.tutor.email}"
    
    
