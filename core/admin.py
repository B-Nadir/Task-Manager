from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from .models import (UserProfile, Task, Reminder, Complaint, Notification, Tag, TaskStep)


# ---------------------------
# Unregister Default User Admin
# ---------------------------
admin.site.unregister(User)


# ---------------------------
# Custom User Admin (with Login As button)
# ---------------------------
@admin.register(User)
class CustomUserAdmin(DefaultUserAdmin):
    list_display = ('id', 'username', 'email', 'is_staff', 'is_superuser', 'last_login', 'login_as_action')

    def login_as_action(self, obj):
        if obj.is_superuser:
            return format_html('<span style="color:gray;">Superuser</span>')
        url = reverse('login_as_user', args=[obj.id])
        return format_html('<a class="button" href="{}">Login As</a>', url)


# ---------------------------
# User Profile Admin
# ---------------------------
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'user_email', 'phone', 'role')

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'


# ---------------------------
# Task Admin
# ---------------------------
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'due_date', 'is_completed', 'created_at')
    list_editable = ('is_completed',)
    search_fields = ('title', 'description', 'user__username')
    list_filter = ('is_completed', 'due_date', 'tags')
    ordering = ('-created_at',)


# ---------------------------
# Task Step Admin
# ---------------------------
@admin.register(TaskStep)
class TaskStepAdmin(admin.ModelAdmin):
    list_display = ('task', 'title', 'order', 'assigned_to', 'is_completed')
    search_fields = ('title', 'task__title')
    list_filter = ('is_completed',)
    ordering = ('task', 'order')


# ---------------------------
# Reminder Admin
# ---------------------------
@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ('task', 'reminder_time')
    search_fields = ('task__title',)
    list_filter = ('reminder_time',)
    ordering = ('-reminder_time',)


# ---------------------------
# Complaint Admin
# ---------------------------
@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('subject', 'user', 'status', 'created_at')
    search_fields = ('subject', 'message', 'user__username')
    list_filter = ('status', 'created_at')
    ordering = ('-created_at',)


# ---------------------------
# Notification Admin
# ---------------------------
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'is_read', 'created_at')
    search_fields = ('message', 'user__username')
    list_filter = ('is_read', 'created_at')
    ordering = ('-created_at',)


# ---------------------------
# Tag Admin
# ---------------------------
@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)