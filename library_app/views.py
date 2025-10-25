from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import HttpResponseForbidden
from datetime import timedelta
from .models import Book, Reader, BorrowRecord, Category


def _get_or_create_reader_from_user(user):
    email = getattr(user, "email", None)
    if not email:
        return None, False
    defaults = {"name": user.get_full_name() or user.username, "phone": ""}
    reader, created = Reader.objects.get_or_create(email=email, defaults=defaults)
    return reader, created

# User Views
def borrow_book(request, book_id):
    book = get_object_or_404(Book, id=book_id)

    if book.available <= 0:
        return render(request, "error.html", {"message": "Sách đã hết hàng!"})

    reader, _ = _get_or_create_reader_from_user(request.user)
    if not reader:
        return render(request, "error.html", {"message": "Tài khoản không có email. Vui lòng cập nhật email."})

    due_date = timezone.now() + timedelta(days=14)
    BorrowRecord.objects.create(reader=reader, book=book, due_date=due_date)
    book.available -= 1
    book.save()

    return redirect("home")

# User Views
def return_book(request, record_id):
    record = get_object_or_404(BorrowRecord, id=record_id)

    reader, _ = _get_or_create_reader_from_user(request.user)
    if not reader:
        return render(request, "error.html", {"message": "Tài khoản không có email. Vui lòng cập nhật email."})

    if record.reader != reader:
        return HttpResponseForbidden("Bạn không có quyền trả cuốn sách này.")

    if not record.return_date:
        record.return_date = timezone.now()
        record.book.available += 1
        record.book.save()
        record.save()

    return redirect("home")


def home(request):
    books = Book.objects.all()
    readers = Reader.objects.all()
    borrow_records = BorrowRecord.objects.filter(return_date__isnull=True)
    return render(request, "home.html", {
        "books": books,
        "readers": readers,
        "borrow_records": borrow_records
    })

# Admin/Staff Views
def add_book(request):
    if request.method == "POST":
        title = request.POST.get("title")
        author = request.POST.get("author")
        category_id = request.POST.get("category")
        quantity = int(request.POST.get("quantity", 0))
        image = request.FILES.get("image")

        category = get_object_or_404(Category, id=category_id) if category_id else None

        book = Book.objects.create(
            title=title,
            author=author,
            category=category,
            quantity=quantity,
            available=quantity,
            image=image
        )
        return redirect("home")
    else:
        categories = Category.objects.all()
        return render(request, "add_book.html", {"categories": categories})

# Admin/Staff Views
def edit_book(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    
    if request.method == "POST":
        # Lấy dữ liệu từ form
        book.title = request.POST.get("title", book.title)
        book.author = request.POST.get("author", book.author)
        category_id = request.POST.get("category")
        book.category = get_object_or_404(Category, id=category_id) if category_id else None
        
        # Cập nhật số lượng nếu có thay đổi
        new_quantity = int(request.POST.get("quantity", book.quantity))
        quantity_change = new_quantity - book.quantity
        book.quantity = new_quantity
        book.available += quantity_change
        
        # Xử lý ảnh mới nếu có
        if "image" in request.FILES:
            # Xóa ảnh cũ nếu có
            if book.image:
                book.image.delete()
            book.image = request.FILES["image"]
            
        book.save()
        return redirect("home")
        
    else:
        categories = Category.objects.all()
        return render(request, "edit_book.html", {
            "book": book,
            "categories": categories
        })

# Admin/Staff Views
def delete_book(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    
    # Kiểm tra xem có phiếu mượn chưa trả không
    active_borrows = BorrowRecord.objects.filter(book=book, return_date__isnull=True).exists()
    if active_borrows:
        return render(request, "error.html", {
            "message": "Không thể xóa sách này vì đang có người mượn!"
        })

    # Xóa ảnh cũ nếu có
    if book.image:
        book.image.delete()
    
    # Xóa sách
    book.delete()
    return redirect("home")

# Admin/Staff Views
def check_inventory(request):
    low_stock_books = Book.objects.filter(available__lt=5)
    return render(request, "inventory.html", {
        "low_stock_books": low_stock_books
    })

# Admin/Staff Views
def check_overdue(request):
    overdue_records = BorrowRecord.objects.filter(
        return_date__isnull=True,
        due_date__lt=timezone.now()
    ).select_related('reader', 'book')
    return render(request, "overdue.html", {
        "overdue_records": overdue_records
    })