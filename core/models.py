from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from typing import Optional

# ---------------------------
# User Profile
# ---------------------------
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    role = models.CharField(max_length=50, default='User')
    phone = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True)

    @property
    def full_name(self):
        full = f"{self.user.first_name} {self.user.last_name}".strip()
        return full if full else self.user.username

    notify_email = models.BooleanField(default=True)
    notify_in_app = models.BooleanField(default=True)
    notify_sound = models.BooleanField(default=True)

    reminder_email = models.BooleanField(default=True)
    reminder_in_app = models.BooleanField(default=True)
    reminder_sound = models.BooleanField(default=True)

    notification_sound = models.FileField(upload_to='sounds/', blank=True, null=True)
    reminder_sound = models.FileField(upload_to='sounds/', blank=True, null=True)

    def __str__(self):
        return self.user.username


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


# ---------------------------
# Tag
# ---------------------------
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    color = models.CharField(max_length=7, default="#FFFFFF")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
    

# ---------------------------
# Task
# ---------------------------
class Task(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    due_date = models.DateTimeField(null=True, blank=True)

    user = models.ForeignKey(User, related_name='created_tasks', on_delete=models.CASCADE)
    assigned_to = models.ManyToManyField(User, related_name='assigned_tasks', blank=True)
    tags = models.ManyToManyField(Tag, blank=True)

    is_completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


# ---------------------------
# Task Step
# ---------------------------
class TaskStep(models.Model):
    task = models.ForeignKey(Task, related_name='steps', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    assigned_to = models.ForeignKey(User, related_name='task_steps', null=True, blank=True, on_delete=models.SET_NULL)
    is_completed = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.task.title} - Step {self.order}: {self.title}"
    

# ---------------------------
# Reminder
# ---------------------------
class Reminder(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='reminders')
    title = models.CharField(max_length=100, default="")
    reminder_time = models.DateTimeField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    is_triggered = models.BooleanField(default=False)

    def __str__(self):
        return f"Reminder: {self.title} for {self.task.title}"


class ReminderTrigger(models.Model):
    reminder = models.ForeignKey(Reminder, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    triggered = models.BooleanField(default=False)

# ---------------------------
# Complaint (Updated for Corporate Context)
# ---------------------------
class Complaint(models.Model):
    COMPLAINT_TYPES = [
        ('IT Support', 'IT Support'),
        ('Human Resources', 'Human Resources'),
        ('Facility Management', 'Facility Management'),
        ('Payroll/Finance', 'Payroll/Finance'),
        ('Operations', 'Operations'),
        ('Compliance', 'Compliance & Policy'),
        ('Software Issue', 'Software/App Issue'),
        ('Feature Request', 'Feature Request'),
        ('Other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Resolved', 'Resolved'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    complaint_type = models.CharField(max_length=25, choices=COMPLAINT_TYPES, default='Other')
    subject = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    tags = models.ManyToManyField(Tag, blank=True, related_name="complaints")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.subject} - {self.status}"
    

# ---------------------------
# Notification
# ---------------------------

class Notification(models.Model):
    # CATEGORY TYPES
    CATEGORY_TASK = "task"
    CATEGORY_COMPLAINT = "complaint"
    CATEGORY_REMINDER = "reminder"
    CATEGORY_SYSTEM = "system"

    CATEGORY_CHOICES = [
        (CATEGORY_TASK, "Task"),
        (CATEGORY_COMPLAINT, "Complaint"),
        (CATEGORY_REMINDER, "Reminder"),
        (CATEGORY_SYSTEM, "System"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.CharField(max_length=255)

    # NEW FIELDS
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_SYSTEM
    )
    related_id = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="ID of task, complaint, or reminder if applicable"
    )
    send_email = models.BooleanField(
        default=False,
        help_text="Whether email notification should be sent"
    )
    
    is_read = models.BooleanField(default=False)
    is_popped = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.category.title()} Notification → {self.user.username}: {self.message[:30]}"


# ---------------------------
# Comment
# ---------------------------
class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, related_name='comments', null=True, blank=True, on_delete=models.CASCADE)
    complaint = models.ForeignKey(Complaint, related_name='comments', null=True, blank=True, on_delete=models.CASCADE)
    parent = models.ForeignKey('self', related_name='replies', null=True, blank=True, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']


# ---------------------------
# Attachment
# ---------------------------
class Attachment(models.Model):
    task = models.ForeignKey(Task, related_name='attachments', null=True, blank=True, on_delete=models.CASCADE)
    complaint = models.ForeignKey(Complaint, related_name='attachments', null=True, blank=True, on_delete=models.CASCADE)
    file = models.FileField(upload_to='attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name