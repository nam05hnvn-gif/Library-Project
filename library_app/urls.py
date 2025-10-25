from django.urls import path
from . import views

app_name = 'library'

urlpatterns = [
    # Các chức năng cơ bản
    path('', views.home, name='home'),
    
    # Chức năng cho user đã đăng nhập
    path('book/borrow/<int:book_id>/', views.borrow_book, name='borrow_book'),
    path('book/return/<int:record_id>/', views.return_book, name='return_book'),
    
    # Chức năng cho admin/staff
    path('book/add/', views.add_book, name='add_book'),
    path('book/edit/<int:book_id>/', views.edit_book, name='edit_book'),
    path('book/delete/<int:book_id>/', views.delete_book, name='delete_book'),
    path('inventory/', views.check_inventory, name='check_inventory'),
    path('overdue/', views.check_overdue, name='check_overdue'),
]