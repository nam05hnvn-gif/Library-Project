from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import HttpResponseForbidden
from datetime import timedelta
from .models import Book, Reader, BorrowRecord, Category
from .form import BookForm
from django.db.models import Q

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy,reverse
from django.contrib.auth.mixins import LoginRequiredMixin

def _get_or_create_reader_from_user(user):
    email = getattr(user, "email", None)
    if not email:
        return None, False
    defaults = {"name": user.get_full_name() or user.username, "phone": ""}
    reader, created = Reader.objects.get_or_create(email=email, defaults=defaults)
    return reader, created

@login_required
def borrow_book(request, book_id):
    if request.method != "POST":
        return redirect("home")

    book = get_object_or_404(Book, id=book_id)

    if book.available <= 0:
        return render(request, "error.html", {"message": "Sách đã hết hàng!"})

    reader, _ = _get_or_create_reader_from_user(request.user)
    if not reader:
        return render(request, "error.html", {"message": "Tài khoản không có email. Vui lòng cập nhật email."})

    due_date = timezone.now() + timedelta(days=14)
    BorrowRecord.objects.create(reader=reader, book=book, due_date=due_date)
    book.available = max(0, book.available - 1)
    book.save()

    return redirect("library:home")

@login_required
def return_book(request, record_id):
    if request.method != "POST":
        return redirect("library:home")

    record = get_object_or_404(BorrowRecord, id=record_id)

    reader, _ = _get_or_create_reader_from_user(request.user)
    if not reader:
        return render(request, "error.html", {"message": "Tài khoản không có email. Vui lòng cập nhật email."})

    if record.reader != reader:
        return HttpResponseForbidden("Bạn không có quyền trả cuốn sách này.")

    if not record.return_date:
        record.return_date = timezone.now()
        book = record.book
        book.available = min(book.quantity, book.available + 1)
        book.save()
        record.save()

    return redirect("library:home")


def home(request):
    query = request.GET.get('q', '').strip()  # Lấy nội dung người dùng nhập
    category_filter = request.GET.get('category', '')  # Nếu có chọn thể loại
    books = Book.objects.all()

    # Nếu có nội dung tìm kiếm
    if query:
        books = books.filter(
            Q(title__icontains=query) |
            Q(author__icontains=query) |
            Q(category__name__icontains=query)            
        ).distinct()

    # Nếu có chọn thể loại cụ thể
    if category_filter:
        books = books.filter(category__name__iexact=category_filter)

    # Thông tin người đọc và phiếu mượn
    readers = Reader.objects.all()
    borrow_records = []
    if request.user.is_authenticated:
        reader, _ = _get_or_create_reader_from_user(request.user)
        if reader:
            borrow_records = BorrowRecord.objects.filter(
                reader=reader,
                return_date__isnull=True
            )

    categories = Category.objects.all().order_by('name')  # Gửi sang để hiển thị dropdown lọc thể loại

    return render(request, "home.html", {
        "books": books,
        "readers": readers,
        "borrow_records": borrow_records,
        "query_search": query,
        "categories": categories,
        "selected_category": category_filter
    })

def is_staff_user(user):
    """Kiểm tra xem người dùng có phải staff hay không"""
    return user.is_staff

@login_required
@user_passes_test(is_staff_user)
def add_book(request):
    if request.method == "POST":
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save(commit=False)
            # Khi thêm sách mới, gán available = quantity
            book.available = book.quantity
            book.save()
            messages.success(request, "Thêm sách thành công")
            return redirect('library:home')
    else:
        form = BookForm()
    return render(request, 'add_book.html', {'form': form})


@login_required
@user_passes_test(is_staff_user)
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
        if book.available < 0:
            book.available = 0
        if book.available > book.quantity:
            book.available = book.quantity
        
        # Xử lý ảnh mới nếu có
        if "image" in request.FILES:
            # Xóa ảnh cũ nếu có
            if book.image:
                book.image.delete(save=False)
            book.image = request.FILES["image"]
            
        book.save()
        return redirect("library:home")
        
    else:
        categories = Category.objects.all()
        return render(request, "edit_book.html", {
            "book": book,
            "categories": categories
        })

@login_required
@user_passes_test(is_staff_user)
def delete_book(request, book_id):
    if request.method != "POST":
        return redirect("library:home")

    book = get_object_or_404(Book, id=book_id)
    
    # Kiểm tra xem có phiếu mượn chưa trả không
    active_borrows = BorrowRecord.objects.filter(book=book, return_date__isnull=True).exists()
    if active_borrows:
        return render(request, "error.html", {
            "message": "Không thể xóa sách này vì đang có người mượn!"
        })

    # Xóa ảnh cũ nếu có
    if book.image:
        book.image.delete(save=False)
    
    # Xóa sách
    book.delete()
    return redirect("library:home")


@login_required
@user_passes_test(is_staff_user) # Chỉ staff mới xem được trang này
def statistics_view(request):
 
    # Đếm tổng số sách (dùng model Book)
    total_books = Book.objects.count()
    
    # Đếm tổng số độc giả (dùng model Reader)
    total_readers = Reader.objects.count()
    
    # Đếm số sách đang được mượn (là những cuốn có 'return_date' bị rỗng)
    borrowed_books_count = BorrowRecord.objects.filter(return_date__isnull=True).count()
    
    # Lấy ngày hôm nay
    today = timezone.now().date()
    
    # Đếm sách quá hạn (là sách có 'due_date' < hôm nay VÀ chưa trả)
    overdue_books_count = BorrowRecord.objects.filter(
        due_date__lt=today, 
        return_date__isnull=True
    ).count()

    # Đóng gói tất cả các con số này lại
    context = {
        'total_books': total_books,
        'total_readers': total_readers,
        'borrowed_books_count': borrowed_books_count,
        'overdue_books_count': overdue_books_count,
    }
    
    return render(request, 'statistics.html', context)

@login_required
@user_passes_test(is_staff_user)
def check_inventory(request):
    low_stock_books = Book.objects.filter(available__lt=5)
    return render(request, "inventory.html", {
        "low_stock_books": low_stock_books
    })

@login_required
@user_passes_test(is_staff_user)
def check_overdue(request):
    overdue_records = BorrowRecord.objects.filter(
        return_date__isnull=True,
        due_date__lt=timezone.now()
    ).select_related('reader', 'book')
    return render(request, "overdue.html", {
        "overdue_records": overdue_records
    })

# Authentication & Role Management module
# Thêm decorator @login_required với các view yêu cầu đăng nhập
# Thêm @user_passes_test(is_staff_user) với các view yêu cầu quyền staff


def login_view(request):
    """Xử lí đăng nhập"""
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is None:
            return render(request,'accounts/login.html',{
                'error':'Tên đăng nhập hoặc mật khẩu không chính xác',
                'username': username
            })
        login(request,user)
        if user.is_superuser:
            return redirect(reverse('admin:index'))
        elif user.is_staff:
            return redirect('library:staff_dashboard')
        else:
            return redirect('library:home')
    return render(request,'accounts/login.html')

def register_view(request):
    """Đăng kí tài khoản mới"""
    if request.method == "POST":
        last_name = request.POST.get('last_name')
        first_name = request.POST.get('first_name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        if not all([last_name,first_name,username,email,password1,password2]):
            return render(request,'accounts/register.html',{
                'error': 'Vui lòng điền đầy đủ thông tin',
                'last_name': last_name,
                'first_name': first_name,
                'username': username,
                'email': email
            })
        if password1 != password2:
            return render(request, 'accounts/register.html', {
                'error': 'Mật khẩu không khớp',
                'first_name': first_name,
                'last_name': last_name,
                'username': username,
                'email': email
            })
        if User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists():
            messages.error(request, 'Tên đăng nhập hoặc email đã tồn tại')
            return redirect('library:register')
        user = User.objects.create_user(
            last_name=last_name,
            first_name=first_name,
            username=username,
            email=email,
            password=password1
        )
        messages.success(request,'Đăng kí tài khoản thành công')
        return redirect('library:login')
    return render(request,'accounts/register.html')
    
@login_required
def logout_view(request):
    """Đăng xuất khỏi tài khoản hiện tại"""
    logout(request)
    return redirect('library:home')

@login_required
def profile(request):
    user = request.user
    return render(request, 'accounts/profile.html', {'user': user})

@login_required
def edit_profile(request):
    """Chỉnh sửa hồ sơ"""
    if request.method == "POST":
        user = request.user
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.save()
        return redirect('library:profile')
    return render(request,'accounts/edit_profile.html')

class UserPasswordChangeView(LoginRequiredMixin,PasswordChangeView):
    """Thay đổi mật khẩu bằng class sẵn có"""
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('library:profile')
    def form_valid(self, form):
        messages.success(self.request, 'Mật khẩu đã được thay đổi thành công')
        return super().form_valid(form)
    def form_invalid(self, form):
        messages.error(self.request, 'Có lỗi khi đổi mật khẩu. Vui lòng thử lại.')
        return super().form_invalid(form)