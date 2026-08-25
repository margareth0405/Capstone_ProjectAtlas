from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import get_user_model
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q, Sum
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import (
    AdminCreatedUserForm,
    AnnouncementForm,
    ContactForm,
    LibraryItemForm,
    RegistrationForm,
    RoleLoginForm,
)
from .models import Announcement, ContactMessage, DownloadEvent, Favorite, LibraryItem, Profile


User = get_user_model()


@require_GET
def robots_txt(request):
    return HttpResponse(
        'User-agent: *\nDisallow: /staff/\n',
        content_type='text/plain',
    )


def _active_role(request):
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return 'administrator'
        profile = getattr(request.user, 'profile', None)
        return profile.role if profile else Profile.Role.STUDENT
    return 'guest'


def _display_name(request):
    if not request.user.is_authenticated:
        return 'Guest'
    return request.user.get_full_name() or request.user.email or request.user.username


def _stats():
    aggregate = LibraryItem.objects.aggregate(
        total_items=Count('id'),
        total_pages=Sum('pages'),
        unique_authors=Count('author', distinct=True),
        unique_types=Count('collection', distinct=True),
    )
    aggregate['total_pages'] = aggregate['total_pages'] or 0
    return aggregate


def _base_context(request, active_page):
    favorite_count = 0
    if request.user.is_authenticated and not request.user.is_staff:
        favorite_count = Favorite.objects.filter(user=request.user).count()
    stats = _stats()
    return {
        'active_page': active_page,
        'active_role': _active_role(request),
        'display_name': _display_name(request),
        'favorite_count': favorite_count,
        'resource_count': stats['total_items'],
        'item_count': stats['total_items'],
        'collection_count': stats['unique_types'],
        'author_count': stats['unique_authors'],
        'stats': stats,
    }


def _safe_next_url(request, fallback):
    candidate = request.POST.get('next') or request.GET.get('next')
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return reverse(fallback)


def _staff_required(view):
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), reverse('admin:login'))
        if not (request.user.is_active and request.user.is_staff):
            raise PermissionDenied
        return view(request, *args, **kwargs)

    wrapped.__name__ = view.__name__
    wrapped.__doc__ = view.__doc__
    return wrapped


@require_GET
def landing(request):
    if request.user.is_authenticated:
        return redirect('library:dashboard')
    return render(request, 'library/landing.html', {'active_role': 'guest'})


@require_http_methods(['GET', 'POST'])
def register(request):
    if request.user.is_authenticated:
        return redirect('library:dashboard')
    requested_role = request.POST.get('role') or request.GET.get('role', Profile.Role.STUDENT)
    selected_role = (
        Profile.Role.TEACHER
        if requested_role == Profile.Role.TEACHER
        else Profile.Role.STUDENT
    )
    form = RegistrationForm(
        request.POST or None,
        initial={'role': selected_role},
        privacy_consent_version=settings.PRIVACY_CONSENT_VERSION,
    )
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        auth_login(request, user)
        request.session.pop('guest_mode', None)
        messages.success(request, 'Your ATLAS account is ready.')
        return redirect('library:dashboard')
    return render(
        request,
        'library/register.html',
        {'form': form, 'active_role': 'guest', 'selected_role': selected_role},
    )


@require_http_methods(['GET', 'POST'])
def login(request):
    if request.user.is_authenticated:
        return redirect('library:dashboard')
    requested_role = request.POST.get('role') or request.GET.get('role', Profile.Role.STUDENT)
    selected_role = (
        Profile.Role.TEACHER
        if requested_role == Profile.Role.TEACHER
        else Profile.Role.STUDENT
    )
    login_data = request.POST.copy() if request.method == 'POST' else None
    if login_data is not None:
        if not login_data.get('email') and login_data.get('username'):
            login_data['email'] = login_data['username']
        login_data['role'] = selected_role
    form = RoleLoginForm(request, login_data, initial={'role': selected_role})
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        profile = user.profile
        profile.privacy_consent_accepted_at = timezone.now()
        profile.privacy_consent_version = settings.PRIVACY_CONSENT_VERSION
        profile.save(
            update_fields=(
                'privacy_consent_accepted_at',
                'privacy_consent_version',
                'updated_at',
            )
        )
        auth_login(request, user)
        request.session.pop('guest_mode', None)
        messages.success(request, f'Welcome back, {_display_name(request)}.')
        return redirect(_safe_next_url(request, 'library:dashboard'))
    return render(
        request,
        'library/login.html',
        {
            'form': form,
            'active_role': 'guest',
            'selected_role': selected_role,
            'next': request.POST.get('next') or request.GET.get('next', ''),
        },
    )


@require_POST
def guest_login(request):
    if request.user.is_authenticated:
        auth_logout(request)
    request.session['guest_mode'] = True
    return redirect('library:dashboard')


@require_POST
def logout(request):
    auth_logout(request)
    request.session.pop('guest_mode', None)
    messages.info(request, 'You have signed out of ATLAS.')
    return redirect('library:landing')


@require_GET
def dashboard(request):
    if not request.user.is_authenticated and not request.session.get('guest_mode'):
        return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
    context = _base_context(request, 'home')
    context.update(
        {
            'recent_items': LibraryItem.objects.order_by('-created_at')[:6],
            'recent_list': LibraryItem.objects.order_by('-created_at')[:6],
            'recent_announcements': Announcement.objects.filter(
                is_published=True,
                published_at__lte=timezone.now(),
            )[:3],
        }
    )
    return render(request, 'library/dashboard.html', context)


@require_GET
def catalog(request):
    items = LibraryItem.objects.all()
    query = request.GET.get('q', '').strip()
    collection = request.GET.get('collection', '').strip()
    if query:
        items = items.filter(
            Q(title__icontains=query)
            | Q(author__icontains=query)
            | Q(call_number__icontains=query)
            | Q(details__icontains=query)
        )
    valid_collections = {value for value, _label in LibraryItem.Collection.choices}
    if collection in valid_collections:
        items = items.filter(collection=collection)
    sort_map = {
        'title': 'title',
        '-title': '-title',
        'author': 'author',
        '-author': '-author',
        'collection': 'collection',
        '-collection': '-collection',
        'newest': '-created_at',
        'oldest': 'created_at',
    }
    sort = request.GET.get('sort', 'title')
    items = items.order_by(sort_map.get(sort, 'title'))
    context = _base_context(request, 'catalog')
    favorite_ids = set()
    if request.user.is_authenticated and not request.user.is_staff:
        favorite_ids = set(
            Favorite.objects.filter(user=request.user).values_list('item_id', flat=True)
        )
    for item in items:
        item.is_favorite = item.pk in favorite_ids
    context.update(
        {
            'items': items,
            'library_items': items,
            'resources': items,
            'favorite_ids': favorite_ids,
            'query': query,
            'selected_collection': collection,
            'selected_sort': sort,
            'collection_choices': LibraryItem.Collection.choices,
        }
    )
    return render(request, 'library/catalog.html', context)


@require_GET
def item_detail(request, pk):
    context = _base_context(request, 'catalog')
    item = get_object_or_404(LibraryItem, pk=pk)
    context['item'] = item
    context['is_favorite'] = (
        request.user.is_authenticated
        and not request.user.is_staff
        and Favorite.objects.filter(user=request.user, item=item).exists()
    )
    return render(request, 'library/item_detail.html', context)


@require_GET
def favorites(request):
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
    if request.user.is_staff:
        raise PermissionDenied
    context = _base_context(request, 'favorites')
    links = Favorite.objects.filter(user=request.user).select_related('item')
    context.update({'favorites': links, 'items': [link.item for link in links]})
    return render(request, 'library/favorites.html', context)


@require_POST
def favorite_toggle(request, pk):
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
    if request.user.is_staff:
        raise PermissionDenied
    item = get_object_or_404(LibraryItem, pk=pk)
    favorite, created = Favorite.objects.get_or_create(user=request.user, item=item)
    if created:
        messages.success(request, f'Added {item.title} to your favorites.')
    else:
        favorite.delete()
        messages.info(request, f'Removed {item.title} from your favorites.')
    return redirect(_safe_next_url(request, 'library:catalog'))


@require_GET
def download(request, pk):
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
    item = get_object_or_404(LibraryItem, pk=pk)
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    ip_address = forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR')
    DownloadEvent.objects.create(
        user=request.user,
        item=item,
        ip_address=ip_address or None,
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
    )
    if item.resource:
        return FileResponse(
            item.resource.open('rb'),
            as_attachment=True,
            filename=Path(item.resource.name).name,
        )
    if item.external_url:
        return redirect(item.external_url)
    messages.warning(request, 'This catalog record does not have a file attached yet.')
    return redirect('library:item_detail', pk=item.pk)


@require_GET
def announcements(request):
    queryset = Announcement.objects.filter(
        is_published=True,
        published_at__lte=timezone.now(),
    )
    category = request.GET.get('category', '').strip()
    valid_categories = {value for value, _label in Announcement.Category.choices}
    if category in valid_categories:
        queryset = queryset.filter(category=category)
    context = _base_context(request, 'announcements')
    featured_announcement = queryset.filter(is_featured=True).first()
    context.update(
        {
            'announcements': queryset,
            'announcement_count': queryset.count(),
            'featured_announcement': featured_announcement,
            'selected_category': category,
            'category_choices': Announcement.Category.choices,
        }
    )
    return render(request, 'library/announcements.html', context)


@require_http_methods(['GET', 'POST'])
def contact(request):
    initial = {}
    if request.user.is_authenticated:
        initial = {
            'name': request.user.get_full_name(),
            'email': request.user.email,
        }
    form = ContactForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        contact_message = form.save(commit=False)
        if request.user.is_authenticated:
            contact_message.user = request.user
        contact_message.save()
        messages.success(request, 'Your message has been sent to the ATLAS team.')
        return redirect('library:contact')
    context = _base_context(request, 'contact')
    context.update(
        {
            'form': form,
            'contact_name': request.user.get_full_name() if request.user.is_authenticated else '',
            'contact_email': request.user.email if request.user.is_authenticated else '',
        }
    )
    return render(request, 'library/contact.html', context)


@_staff_required
@require_GET
def staff_portal(request):
    users = User.objects.select_related('profile').order_by('-date_joined')
    context = _base_context(request, 'home')
    student_count = users.filter(profile__role=Profile.Role.STUDENT).count()
    teacher_count = users.filter(profile__role=Profile.Role.TEACHER).count()
    context['stats'].update(
        {
            'total_users': users.count(),
            'student_users': student_count,
            'teacher_users': teacher_count,
            'successful_logins': users.filter(last_login__isnull=False).count(),
        }
    )
    context.update(
        {
            'items': LibraryItem.objects.order_by('-created_at'),
            'recent_items': LibraryItem.objects.order_by('-created_at')[:8],
            'announcements': Announcement.objects.all(),
            'recent_announcements': Announcement.objects.all()[:6],
            'users': users,
            'user_count': users.count(),
            'download_count': DownloadEvent.objects.count(),
            'message_count': ContactMessage.objects.filter(is_resolved=False).count(),
            'item_form': LibraryItemForm(),
            'announcement_form': AnnouncementForm(),
            'user_form': AdminCreatedUserForm(),
        }
    )
    return render(request, 'library/staff_portal.html', context)


@_staff_required
@require_http_methods(['GET', 'POST'])
def staff_item_create(request):
    form = LibraryItemForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        item.created_by = request.user
        item.save()
        messages.success(request, f'{item.title} was added to the library.')
        return redirect('library:staff_portal')
    context = _base_context(request, 'catalog')
    context.update({'form': form, 'form_title': 'Add library item', 'submit_label': 'Add item'})
    return render(request, 'library/admin/item_form.html', context)


@_staff_required
@require_http_methods(['GET', 'POST'])
def staff_item_edit(request, pk):
    item = get_object_or_404(LibraryItem, pk=pk)
    form = LibraryItemForm(request.POST or None, request.FILES or None, instance=item)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'{item.title} was updated.')
        return redirect('library:staff_portal')
    context = _base_context(request, 'catalog')
    context.update({'form': form, 'form_title': 'Edit library item', 'submit_label': 'Save changes'})
    return render(request, 'library/admin/item_form.html', context)


@_staff_required
@require_POST
def staff_item_delete(request, pk):
    item = get_object_or_404(LibraryItem, pk=pk)
    title = item.title
    item.delete()
    messages.info(request, f'{title} was removed from the library.')
    return redirect('library:staff_portal')


@_staff_required
@require_http_methods(['GET', 'POST'])
def staff_announcement_create(request):
    form = AnnouncementForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        announcement = form.save(commit=False)
        announcement.created_by = request.user
        announcement.save()
        messages.success(request, 'Announcement published.')
        return redirect('library:staff_portal')
    context = _base_context(request, 'announcements')
    context.update({'form': form, 'form_title': 'Create announcement', 'submit_label': 'Save announcement'})
    return render(request, 'library/admin/announcement_form.html', context)


@_staff_required
@require_http_methods(['GET', 'POST'])
def staff_announcement_edit(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)
    form = AnnouncementForm(request.POST or None, instance=announcement)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Announcement updated.')
        return redirect('library:staff_portal')
    context = _base_context(request, 'announcements')
    context.update({'form': form, 'form_title': 'Edit announcement', 'submit_label': 'Save changes'})
    return render(request, 'library/admin/announcement_form.html', context)


@_staff_required
@require_POST
def staff_announcement_delete(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk)
    announcement.delete()
    messages.info(request, 'Announcement deleted.')
    return redirect('library:staff_portal')


@_staff_required
@require_http_methods(['GET', 'POST'])
def staff_user_create(request):
    form = AdminCreatedUserForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        messages.success(request, f'Account created for {user.email}.')
        return redirect('library:staff_portal')
    context = _base_context(request, 'users')
    context.update({'form': form, 'form_title': 'Create account', 'submit_label': 'Create account'})
    return render(request, 'library/admin/user_form.html', context)
