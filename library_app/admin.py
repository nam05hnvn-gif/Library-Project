from django.contrib import admin
from .models import Book, Reader, BorrowRecord, Category

admin.site.register(Book)
admin.site.register(Reader)
admin.site.register(BorrowRecord)
admin.site.register(Category)
