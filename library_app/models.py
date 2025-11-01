from django.db import models
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=0)
    available = models.PositiveIntegerField(default=0)  # số sách còn
    image = models.ImageField(upload_to="book_images/", null=True, blank=True)

    def __str__(self):
        return self.title


class Reader(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class BorrowRecord(models.Model):
    reader = models.ForeignKey(Reader, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    borrow_date = models.DateTimeField(default=timezone.now)
    due_date = models.DateTimeField()
    return_date = models.DateTimeField(null=True, blank=True)

    def is_overdue(self):
        return not self.return_date and timezone.now() > self.due_date

    def __str__(self):
        return f"{self.reader.name} → {self.book.title}"
