from django.contrib import admin
from django.urls import path
from core import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [

    path('', views.dashboard, name='dashboard'),
    path('admin/', admin.site.urls),
    path('users/', views.user_list, name='user_list'),
    path('users/login-as/<int:user_id>/', views.login_as_user, name='login_as_user'),
    path('switch-back/', views.switch_back, name='switch_back'),
    
    # Authentication URLs
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Task Management URLs
    path('tasks/', views.task_list, name='task_list'),
    path('tasks/create/', views.create_task, name='create_task'),
    path('tasks/edit/<int:pk>/', views.edit_task, name='edit_task'),
    path('tasks/<int:pk>/complete/', views.mark_task_completed, name='mark_task_completed'),
    path('tasks/delete/<int:pk>/', views.delete_task, name='delete_task'),

    # Reminder Management URLs
    path('reminders/', views.reminder_list, name='reminder_list'),
    path('reminders/create/', views.create_reminder, name='create_reminder'),
    path('reminders/edit/<int:pk>/', views.edit_reminder, name='edit_reminder'),
    path('reminders/delete/<int:pk>/', views.delete_reminder, name='delete_reminder'),

    # Complaint Management URLs
    path('complaints/', views.complaint_list, name='complaint_list'),
    path('complaints/create/', views.create_complaint, name='create_complaint'),
    path('complaints/<int:pk>/resolve/', views.resolve_complaint, name='resolve_complaint'),
    path('complaints/edit/<int:pk>/', views.edit_complaint, name='edit_complaint'),
    path('complaints/<int:pk>/delete/', views.delete_complaint, name='delete_complaint'),

    # Notification List URL
    path("notifications/", views.notification_list, name="notification_list"),
    path("notifications/<int:pk>/read/", views.mark_notification_read, name="mark_notification_read"),
    path("notifications/read-all/", views.mark_all_notifications_read, name="mark_all_notifications_read"),

    # History URLs
    path('history/', views.history_log, name='history_log'),
    path('history/export/', views.export_history, name='export_history'),

    # User Profile URLs
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/change-password/', views.change_password, name='password_change'),

    # Task Detail
    path('tasks/<int:pk>/', views.task_detail, name='task_detail'),

    # Complaint Detail
    path('complaints/<int:pk>/detail/', views.complaint_detail, name='complaint_detail'),

    # Tags
    path('tags/', views.tag_master, name='tag_master'),
    path('tags/create/', views.create_tag, name='create_tag'),
    path('tags/edit/<int:pk>/', views.edit_tag, name='edit_tag'),
    path('tags/delete/<int:pk>/', views.delete_tag, name='delete_tag'),

    path('check_reminders/', views.check_due_reminders, name='check_reminders'),
    path('check_notifications/', views.check_new_notifications, name='check_new_notifications'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)