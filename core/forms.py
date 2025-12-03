from django import forms
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from .models import (Task, Reminder, Complaint, UserProfile, Comment, Tag)
from typing import cast
from django.forms import ModelMultipleChoiceField


# ========================================
# TASK FORM
# ========================================
class TaskForm(forms.ModelForm):
    new_tags = forms.CharField(
        required=False,
        label="Create New Tags (comma separated)")

    attachments = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': False}), required=False)
    
    class Meta:
        model = Task
        fields = [
            'title', 'description', 'due_date',
            'tags', 'assigned_to', 'attachments',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 rounded-xl border border-soft bg-white focus:border-primary focus:ring-2 focus:ring-primary/30',
                'placeholder': 'Task Title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 rounded-xl border border-soft bg-white resize-none min-h-[130px] focus:border-primary focus:ring-2 focus:ring-primary/30',
                'rows': 3,
                'placeholder': 'Task Description'
            }),
            'due_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full px-4 py-2 rounded-xl border border-soft bg-white text-center focus:border-primary focus:ring-2 focus:ring-primary/30'
            }),
            'tags': forms.CheckboxSelectMultiple(),
            'assigned_to': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Assign Users queryset
        if user and user.is_superuser:
            self.fields['assigned_to'].queryset = User.objects.filter(is_superuser=False) #type: ignore
        else:
            self.fields['assigned_to'].queryset = User.objects.exclude(is_superuser=True) #type: ignore

        # ★ Override label to FULL NAME
        self.fields['assigned_to'].label_from_instance = (  #type: ignore
            lambda obj: (
                f"{obj.first_name} {obj.last_name}".strip() 
                if obj.first_name or obj.last_name 
                else obj.username
            )
        )

        # Tags also full-name friendly format
        self.fields['tags'] = ModelMultipleChoiceField(
            queryset=Tag.objects.all(),
            widget=forms.CheckboxSelectMultiple()
        )

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('assigned_to'):
            raise forms.ValidationError("Please assign the task to at least one user.")
        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        task = super().save(commit=False)
        if commit:
            task.save()
            self.save_m2m()

            # Handle new tags
            new_tags = self.cleaned_data.get('new_tags', '').strip()
            if new_tags:
                for name in [t.strip() for t in new_tags.split(',') if t.strip()]:
                    tag, _ = Tag.objects.get_or_create(name=name)
                    task.tags.add(tag)
        return task


# ========================================
# REMINDER FORM
# ========================================
class ReminderForm(forms.ModelForm):
    class Meta:
        model = Reminder
        fields = ['title', 'task', 'reminder_time']  # ← Add title here!
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': "Reminder Title",
                'class': "w-full border border-soft px-4 py-2 rounded-xl shadow-sm focus:border-primary"
            }),
            'task': forms.Select(attrs={
                'class': 'w-full px-4 py-2 rounded-xl border border-soft bg-white shadow-sm'
            }),
            'reminder_time': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'w-full px-4 py-2 rounded-xl border border-soft bg-white shadow-sm'
            })
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Accept user argument
        super().__init__(*args, **kwargs)

        if user and not user.is_superuser:
            self.fields['task'].queryset = Task.objects.filter(Q(created_by=user) | Q(assigned_to=user) # type: ignore
            )  

    def clean_reminder_time(self):
        reminder_time = self.cleaned_data.get('reminder_time')
        if reminder_time and reminder_time <= timezone.now():
            raise forms.ValidationError("Reminder time must be in the future.")
        return reminder_time


# ========================================
# COMPLAINT FORM
# ========================================
class ComplaintForm(forms.ModelForm):
    attachments = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': False}), required=False)
    class Meta:
        model = Complaint
        fields = ['complaint_type', 'subject', 'message', 'attachments', 'tags']
        widgets = {
            'complaint_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-soft bg-white focus:border-primary'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 rounded-lg border border-soft bg-white',
                'placeholder': 'Enter complaint subject'
            }),
            'message': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-4 py-2 rounded-lg border border-soft bg-white',
                'placeholder': 'Describe your issue clearly...'
            }),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tags"].queryset = Tag.objects.all() # type: ignore
        self.fields["tags"].widget.attrs.update({
            "class": "border border-soft rounded-lg px-3 py-2 w-full"
        })


# ========================================
# PROFILE FORMS
# ========================================
class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

class UserProfileForm(forms.ModelForm):
    avatar = forms.ImageField(required=False)

    class Meta:
        model = UserProfile
        fields = ['avatar', 'phone', 'bio']


# ========================================
# COMMENT FORM
# ========================================
class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 2, 'class': 'input-element', 'placeholder': 'Write a comment...'})
        }


# ========================================
# TAG FORM
# ========================================
class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ['name', 'color', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input-element', 'placeholder': 'Tag name'}),
            'description': forms.Textarea(attrs={'class': 'input-element', 'rows': 2, 'placeholder': 'Optional description'}),
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'w-16 h-10 rounded'}),
        }