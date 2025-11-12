from django.urls import path
from . import views

app_name = 'library'

urlpatterns = [
    # Các chức năng cơ bản
    path('', views.home, name='home'),
    
    # Chức năng cho user đã đăng nhập
    path('book/borrow/<int:book_id>/', views.borrow_book, name='borrow-book'),
    path('book/return/<int:record_id>/', views.return_book, name='return-book'),


    # Auth / profile
    path('accounts/login/', views.login_view, name='login'),
    path('accounts/logout/', views.logout_view, name='logout'),
    path('accounts/register/', views.register_view, name='register'),
    path('profile/edit/', views.edit_profile, name='profile'),
    path('accounts/staff/', views.staff_dashboard, name='staff_dashboard'),
    path('accounts/password-change/', views.UserPasswordChangeView.as_view(), name='password_change'),
    
    # Chức năng cho admin/staff
    path('book/add/', views.add_book, name='add_book'),
    path('book/edit/<int:book_id>/', views.edit_book, name='edit_book'),
    path('book/delete/<int:book_id>/', views.delete_book, name='delete_book'),
    path('inventory/', views.check_inventory, name='check_inventory'),
    path('overdue/', views.check_overdue, name='check_overdue'),

    path('statistics/', views.statistics_view, name='statistics'),
]