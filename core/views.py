from django.db.models.signals import post_save, pre_delete
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q, Max, Count
from django.contrib.auth.models import User
from django.urls import reverse, reverse_lazy
from datetime import timedelta, date
from django.contrib.auth.views import PasswordChangeView
from django.db import models
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from .models import (UserProfile, Task, Reminder, Notification, Complaint, Comment, Attachment, Tag)
from .forms import (TaskForm, ReminderForm, UserForm, ComplaintForm, UserProfileForm, CommentForm, TagForm)
from django.conf import settings
import csv

# ---------------------------
# Dashboard View
# ---------------------------
@login_required
def dashboard(request):
    user = request.user

    # Unique task counts
    total_tasks = Task.objects.filter(
        Q(user=user) | Q(assigned_to=user)
    ).distinct().count()

    completed_tasks = Task.objects.filter(
        Q(user=user) | Q(assigned_to=user),
        is_completed=True
    ).distinct().count()

    pending_tasks = Task.objects.filter(
        Q(user=user) | Q(assigned_to=user),
        is_completed=False
    ).distinct().count()

    # Debug counters (optional display)
    created_by_me = Task.objects.filter(user=user).distinct().count()
    assigned_to = Task.objects.filter(assigned_to=user).distinct().count()

    # Progress percentage (avoids division error)
    progress_percent = round((completed_tasks / total_tasks) * 100, 1) if total_tasks > 0 else 0

    now = timezone.now()
    upcoming_cutoff = now + timedelta(days=7)

    upcoming_reminders = Reminder.objects.filter(
        task__assigned_to=user,
        reminder_time__range=(now, upcoming_cutoff)
    ).count()

    total_complaints = Complaint.objects.count()
    pending_complaints = Complaint.objects.filter(status='Pending').count()
    resolved_complaints = Complaint.objects.filter(status="Resolved").count()

    notifications_unread = Notification.objects.filter(user=user, is_read=False).count()

    task_progress = round((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0
    complaint_progress = round((resolved_complaints / total_complaints) * 100) if total_complaints > 0 else 0

    progress_metrics = [
        {"label": "Task", "value": task_progress, "color": "#2F5A5F"},
        {"label": "Complaint", "value": complaint_progress, "color": "#C9A75D"},
    ]

    context = {
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'created_by_me': created_by_me,
        'assigned_to': assigned_to,
        'upcoming_reminders': upcoming_reminders,
        'total_complaints': total_complaints,
        'pending_complaints': pending_complaints,
        'notifications_unread': notifications_unread,
        'task_progress': task_progress,
        'complaint_progress': complaint_progress,
        'resolved_complaints': resolved_complaints,
        'progress_metrics': progress_metrics,
    }

    return render(request, 'core/dashboard.html', context)


# ---------------------------
# Login/Logout View
# ---------------------------
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f"Welcome back, {user.username}!")
                return redirect('dashboard')
        messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()    
    return render(request, 'core/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "You have successfully logged out.") 
    return redirect('login')


# ---------------------------
# LOGIN AS USER (ADMIN ONLY)
# ---------------------------
@login_required
def login_as_user(request, user_id):
    if not request.user.is_superuser:
        raise PermissionDenied("Only administrators can use login-as.")

    target_user = get_object_or_404(User, id=user_id, is_superuser=False)

    original_admin = request.user.username   # store before login

    backend = 'django.contrib.auth.backends.ModelBackend'
    login(request, target_user, backend=backend)  # perform login as target

    # Now set session value (AFTER login)
    request.session['original_admin'] = original_admin
    request.session.modified = True

    messages.warning(request, f"You are now logged in as {target_user.username}.")
    return redirect('dashboard')

@login_required
def switch_back(request):
    original_admin = request.session.get('original_admin')
    if not original_admin:
        messages.error(request, "No admin session found.")
        return redirect('dashboard')

    admin_user = get_object_or_404(User, username=original_admin)

    backend = 'django.contrib.auth.backends.ModelBackend'
    login(request, admin_user, backend=backend)

    # Clear session
    if 'original_admin' in request.session:
        del request.session['original_admin']
    request.session.modified = True

    messages.success(request, "You are now back as Admin.")
    return redirect('dashboard')


# ---------------------------
# User List View (admin only)
# ---------------------------
@login_required
def user_list(request):
    if not request.user.is_superuser:
        return redirect('dashboard')  # Only admin can view users

    users = User.objects.exclude(id=request.user.id).order_by('username')
    search = request.GET.get('search', '')

    if search:
        users = users.filter(Q(username__icontains=search) | Q(email__icontains=search))

    return render(request, 'core/user_list.html', {'users': users})


# ---------------------------
# Task Views
# ---------------------------
@login_required
def task_list(request):
    user = request.user
    tasks = Task.objects.filter(
        Q(user=user) | Q(assigned_to=user)
    ).order_by('-created_at').distinct()

    tag_filter = request.GET.get('tag')
    if tag_filter:
        if tag_filter.isdigit():
            tasks = tasks.filter(tags__id=int(tag_filter))
        else:
            tasks = tasks.filter(tags__name__iexact=tag_filter)

    search_query = request.GET.get('search', '')
    if search_query:
        tasks = tasks.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(assigned_to__username__icontains=search_query)
        )

    status_filter = request.GET.get('status')
    if status_filter == 'completed':
        tasks = tasks.filter(is_completed=True)
    elif status_filter == 'pending':
        tasks = tasks.filter(is_completed=False)

    role_filter = request.GET.get('role')
    if role_filter == 'assigned_to_me':
        tasks = tasks.filter(assigned_to=user)
    elif role_filter == 'created_by_me':
        tasks = tasks.filter(user=user)

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date:
        tasks = tasks.filter(due_date__date__gte=start_date)
    if end_date:
        tasks = tasks.filter(due_date__date__lte=end_date)

    # PAGINATION
    paginator = Paginator(tasks, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'tasks': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'role_filter': role_filter,
        'start_date': start_date,
        'end_date': end_date,
        'available_tags': Tag.objects.all(),
        'tag_filter': tag_filter,
    }
    return render(request, 'core/task_list.html', context)

@login_required
def task_detail(request, pk):
    task = get_object_or_404(Task, id=pk)

    if not request.user.is_superuser and task.user != request.user and request.user not in task.assigned_to.all():
        messages.error(request, "You do not have access to view this task.")
        return redirect('task_list')

    comments = Comment.objects.filter(task=task, parent__isnull=True)
    attachments = Attachment.objects.filter(task=task)

    return render(request, 'core/task_detail.html', {
        'task': task,
        'form': CommentForm(),
        'comments': comments,
        'attachments': attachments,
        })

@login_required
def create_task(request):
    task = Task()
    if request.method == 'POST':
        form = TaskForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.is_completed = False
            task.save()
            form.save_m2m()

            # Save attachments
            for file in request.FILES.getlist('attachments'):
                Attachment.objects.create(task=task, file=file)

            messages.success(request, "Task created successfully!")
            return redirect('task_detail', pk=task.id)
    else:
        form = TaskForm(user=request.user)
    return render(request, 'core/task_form.html', {"form": form, "title": "Add Task"})

@login_required
def edit_task(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if request.method == 'POST':
        form = TaskForm(request.POST, request.FILES, instance=task, user=request.user)
        if form.is_valid():
            task.is_completed = False
            task = form.save()
            form.save_m2m()

            for file in request.FILES.getlist('attachments'):
                Attachment.objects.create(task=task, file=file)

            messages.success(request, "Task updated successfully.")
            return redirect('task_detail', pk=task.id)
    else:
        form = TaskForm(instance=task, user=request.user)
    return render(request, 'core/task_form.html', {"form": form, "title": "Edit Task"})

@login_required
def mark_task_completed(request, pk) -> HttpResponse:
    task = get_object_or_404(Task, pk=pk)
    if request.user in task.assigned_to.all() or request.user.is_superuser:
        task.is_completed = True
        task.save()

        messages.success(request, "Task marked as completed.")
    else:
        messages.error(request, "You are not allowed to complete this task.")
    return redirect('task_detail', pk=task.pk)

@login_required
def delete_task(request, pk):
    task = get_object_or_404(Task, pk=pk)
    task.delete()
    messages.warning(request, f'Task deleted successfully.')
    return redirect('task_list')


# ---------------------------
# Complaint Views
# ---------------------------
@login_required
def complaint_list(request):
    complaints = Complaint.objects.all().order_by('-created_at')

    # 1. Search Filter
    search_query = request.GET.get('search', '')
    if search_query:
        complaints = complaints.filter(
            Q(subject__icontains=search_query) |
            Q(message__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )

    # 2. Status Filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        complaints = complaints.filter(status=status_filter)

    # 3. Tag Filter
    tag_filter = request.GET.get('tag', '')
    if tag_filter:
        complaints = complaints.filter(tags__id=tag_filter)

    # 4. TYPE FILTER (Added this back for you)
    type_filter = request.GET.get('complaint_type', '')
    if type_filter:
        complaints = complaints.filter(complaint_type=type_filter)

    # Pagination
    paginator = Paginator(complaints.distinct(), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'core/complaint_list.html', {
        'complaints': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'tag_filter': tag_filter,
        'type_filter': type_filter,
        'available_tags': Tag.objects.all(),
        'complaint_types': Complaint.COMPLAINT_TYPES,
    })

@login_required
def complaint_detail(request, pk):
    complaint = get_object_or_404(Complaint, id=pk)

    if not request.user.is_superuser and request.user != complaint.user:
        messages.error(request, "You do not have access to view this complaint.")
        return redirect('complaint_list')

    comments = Comment.objects.filter(complaint=complaint, parent__isnull=True)
    attachments = Attachment.objects.filter(complaint=complaint)

    return render(request, 'core/complaint_detail.html', {
        'complaint': complaint,
        'form': CommentForm(),
        'comments': comments,
        'attachments': attachments,
        'can_edit': request.user.is_superuser or request.user == complaint.user,
    })

@login_required
def create_complaint(request):
    if request.method == 'POST':
        form = ComplaintForm(request.POST, request.FILES)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.user = request.user
            complaint.save()
            form.save_m2m()

            messages.success(request, "Complaint submitted successfully.")
            return redirect('complaint_list')

        else:
            messages.error(request, "Please correct the highlighted errors.")
    else:
        form = ComplaintForm()

    return render(request, 'core/complaint_form.html', {'form': form, 'title': 'Submit Complaint'})

@login_required
def edit_complaint(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk)

    # Only admin can edit
    if not request.user.is_superuser:
        messages.error(request, "Only admin can edit complaints.")
        return redirect('complaint_detail', pk=pk)

    if request.method == 'POST':
        form = ComplaintForm(request.POST, request.FILES, instance=complaint)
        if form.is_valid():
            form.save()

            if request.FILES.getlist('attachments'):
                Attachment.objects.filter(complaint=complaint).delete()
                for file in request.FILES.getlist('attachments'):
                    Attachment.objects.create(complaint=complaint, file=file)

            messages.success(request, "Complaint updated successfully.")
            return redirect('complaint_detail', pk=pk)
    else:
        form = ComplaintForm(instance=complaint)

    return render(request, 'core/complaint_form.html', {'form': form, 'title': 'Edit Complaint'})

@login_required
def resolve_complaint(request, pk) -> HttpResponse:
    if not request.user.is_superuser:
        messages.error(request, "Only admin can resolve complaints.")
        return redirect('complaint_list')

    complaint = get_object_or_404(Complaint, pk=pk)
    complaint.status = 'Resolved'
    complaint.save()

    messages.info(request, "Complaint resolved successfully.")
    return redirect('complaint_detail', pk=pk)


@login_required
def delete_complaint(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Only admin can delete complaints.")
        return redirect('complaint_list')

    complaint = get_object_or_404(Complaint, pk=pk)
    Attachment.objects.filter(complaint=complaint).delete()
    complaint.delete()

    messages.warning(request, "Complaint deleted successfully.")
    return redirect('complaint_list')


#---------------------------
# Reminder Views
#---------------------------
@login_required
def reminder_list(request):
    reminders = Reminder.objects.filter(
        Q(task__assigned_to=request.user) | Q(created_by=request.user)
    ).order_by('-reminder_time').distinct()

    # SEARCH
    search_query = request.GET.get('search', '')
    if search_query:
        reminders = reminders.filter(
            Q(task__title__icontains=search_query)
        )

    # DATE FILTER
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date:
        reminders = reminders.filter(reminder_time__date__gte=start_date)

    if end_date:
        reminders = reminders.filter(reminder_time__date__lte=end_date)

    # PAGINATION – 10 per page
    paginator = Paginator(reminders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'core/reminder_list.html', {
        'reminders': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
        'start_date': start_date,
        'end_date': end_date
    })

@login_required
def reminder_detail(request, pk):
    reminder = get_object_or_404(Reminder, pk=pk)

    if not request.user.is_superuser:
        if reminder.created_by != request.user and request.user not in reminder.task.assigned_to.all():
            messages.error(request, "You do not have permission to view this reminder.")
            return redirect('reminder_list')

    return render(request, 'core/reminder_detail.html', {
        'reminder': reminder,
        'task': reminder.task,
        'can_edit': reminder.created_by == request.user or request.user.is_superuser,
    })

@login_required
def create_reminder(request) -> HttpResponse:
    if request.method == 'POST':
        form = ReminderForm(request.POST, user=request.user)
        if form.is_valid():
            reminder = form.save(commit=False)
            reminder.created_by = request.user
            reminder.save()

            messages.success(request, "Reminder created successfully.")
            return redirect('reminder_list')

    else:
        form = ReminderForm(user=request.user)

    return render(request, 'core/reminder_form.html', {
        'form': form,
        'title': 'Create Reminder',
    })

@login_required
def edit_reminder(request, pk):
    reminder = get_object_or_404(Reminder, pk=pk)
    if request.method == 'POST':
        form = ReminderForm(request.POST, instance=reminder)
        if form.is_valid():
            reminder = form.save(commit=False)
            reminder.is_triggered = False
            reminder.save()
            messages.success(request, "Reminder updated successfully!")
            return redirect('reminder_list')
        else:
            messages.error(request, "Please correct the highlighted errors.")
    else:
        form = ReminderForm(instance=reminder)

    return render(request, 'core/reminder_form.html', {
        'form': form,
        'title': 'Edit Reminder',
    })

@login_required
def check_due_reminders(request):
    now = timezone.now()

    # Only reminders relevant to logged-in user
    reminders = Reminder.objects.filter(
        reminder_time__lte=now,
        is_triggered=False
    ).filter(
        Q(task__assigned_to=request.user) |
        Q(created_by=request.user)
    ).distinct()

    # Mark reminders as triggered ONLY for this user
    for r in reminders:
        r.is_triggered = True
        r.save()

    return JsonResponse({
        "has_due": reminders.exists(),
        "reminders": [
            {"id": r.pk, "title": r.title, "task": r.task.title}
            for r in reminders
        ]
    })

@login_required
def delete_reminder(request, pk):
    reminder = get_object_or_404(Reminder, pk=pk)
    reminder.delete()
    messages.warning(request, 'Reminder deleted successfully.')
    return redirect('reminder_list')


#---------------------------
# History Log View
#---------------------------
@login_required
def history_log(request):
    """
    Display history in the app (optional)
    """
    user = request.user
    tasks = Task.objects.filter(user=user)
    complaints = Complaint.objects.filter(user=user)
    reminders = Reminder.objects.filter(created_by=user)

    context = {
        'tasks': tasks,
        'complaints': complaints,
        'reminders': reminders,
    }
    return render(request, 'core/history_log.html', context)

@login_required
def export_history(request):
    """
    Export all tasks, complaints, and reminders as a CSV file
    """
    user = request.user

    # Create the HttpResponse object with CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="history_log.csv"'

    writer = csv.writer(response)
    writer.writerow(['Type', 'Title/Subject', 'Status', 'Date/Time'])

    # Tasks
    tasks = Task.objects.filter(user=user).order_by('-created_at')
    for task in tasks:
        status = 'Completed' if task.is_completed else 'Pending'
        writer.writerow([
            'Task', 
            task.title, 
            status, 
            task.created_at.strftime('%d-%m-%Y %H:%M')
        ])

    # Complaints
    complaints = Complaint.objects.filter(user=user).order_by('-created_at')
    for complaint in complaints:
        writer.writerow([
            'Complaint', 
            complaint.subject, 
            complaint.status, 
            complaint.created_at.strftime('%d-%m-%Y %H:%M')
        ])

    # Reminders
    reminders = Reminder.objects.filter(created_by=user).order_by('-reminder_time')
    for reminder in reminders:
        writer.writerow([
            'Reminder', 
            reminder.title, 
            '', 
            reminder.reminder_time.strftime('%d-%m-%Y %H:%M')
        ])

    return response


#---------------------------
# Notification List View
#--------------------------
@login_required
def notification_list(request):
    """
    Show notifications with pagination, filters and basic date grouping.
    """
    qs = Notification.objects.filter(user=request.user).order_by('-created_at')

    # --- FILTERS ---

    # Status filter: all / unread / read
    status_filter = request.GET.get('status', '')
    if status_filter == 'unread':
        qs = qs.filter(is_read=False)
    elif status_filter == 'read':
        qs = qs.filter(is_read=True)

    # Category filter: task / complaint / reminder / system
    category_filter = request.GET.get('category', '')
    if category_filter:
        qs = qs.filter(category=category_filter)

    # Date filters (expecting YYYY-MM-DD from <input type="date">)
    start_date = request.GET.get('start_date')  # string or None
    end_date = request.GET.get('end_date')

    if start_date:
        qs = qs.filter(created_at__date__gte=start_date)
    if end_date:
        qs = qs.filter(created_at__date__lte=end_date)

    # --- PAGINATION ---
    paginator = Paginator(qs, 10)  # 10 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # --- DATE GROUPING HELPERS ---
    today = date.today()
    yesterday = today - timedelta(days=1)

    context = {
        'notifications': page_obj,
        'today': today,
        'yesterday': yesterday,
        'notifications_unread': Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count(),
        # Pass filters back to template so the UI can keep state
        'status_filter': status_filter,
        'category_filter': category_filter,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'core/notification_list.html', context)

@login_required
def mark_notification_read(request, pk):
    """
    Mark a single notification as read.
    """
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    return redirect('notification_list')

@login_required
def mark_all_notifications_read(request):
    """
    Mark all notifications for the current user as read.
    """
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect('notification_list')

@login_required
def check_new_notifications(request):
    qs = Notification.objects.filter(user=request.user, is_read=False, is_popped=False)

    if qs.exists():
        # Get the newest notification
        notif = qs.latest('created_at')
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        notif.is_popped = True   # mark as shown
        notif.save()

        return JsonResponse({
            "count": unread_count,
            'has_new': True,
            'title': notif.message[:50] if notif.message else "Notification",
            'message': notif.message,
            'category': notif.category,
        })

    return JsonResponse({'has_new': False})


#---------------------------
# Profile Views
#---------------------------
@login_required
def profile_view(request):
    profile = request.user.userprofile
    
    return render(request, 'core/profile.html', {'user': request.user,})

@login_required
def edit_profile(request):
    user_form = UserForm(instance=request.user)
    profile_form = UserProfileForm(instance=request.user.userprofile)
    file_name = request.user.userprofile.avatar.name.split("/")[-1] if request.user.userprofile.avatar else None

    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=request.user.userprofile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('profile')        

    return render(request, 'core/edit_profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'file_name': file_name
    })

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            messages.success(request, "Password changed successfully.")
            return redirect('profile')
    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, 'core/change_password.html', {'form': form})


# ---------------------------
# Tag Master Views
# ---------------------------
@login_required
def tag_master(request):
    return render(request, 'core/tag_master.html', {'tags': Tag.objects.all().order_by('name')})

@login_required
def create_tag(request):
    if request.method == "POST":
        form = TagForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Tag created successfully!")
            return redirect('tag_master')
    else:
        form = TagForm()
    return render(request, 'core/tag_form.html', {'form': form, 'title': 'Create Tag'})

@login_required
def edit_tag(request, pk):
    tag = get_object_or_404(Tag, pk=pk)
    if request.method == "POST":
        form = TagForm(request.POST, instance=tag)
        if form.is_valid():
            form.save()
            messages.success(request, "Tag updated successfully!")
            return redirect('tag_master')
    else:
        form = TagForm(instance=tag)
    return render(request, 'core/tag_form.html', {'form': form, 'title': 'Edit Tag'})

@login_required
def delete_tag(request, pk):
    tag = get_object_or_404(Tag, pk=pk)
    tag.delete()
    messages.warning(request, f'Tag "{tag.name}" deleted successfully.')
    return redirect('tag_master')