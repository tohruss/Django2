from urllib.request import Request

from django.http import HttpResponse, Http404
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy


from .forms import ChangeUserInfoForm, ChangeStatusForm, CategoryForm
from .models import AdvUser, Category
from django.contrib.auth.views import PasswordChangeView
from .forms import RegisterUserForm
from django.views.generic import UpdateView, CreateView, TemplateView, DeleteView

from .forms import CreateRequestForm
from .models import CreateRequest
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.exceptions import ObjectDoesNotExist

def index(request):
    completed_requests = CreateRequest.objects.filter(status='completed').order_by('-timestamp')[:4]
    in_progress_count = CreateRequest.objects.filter(status='in_progress').count()
    context = {
        'completed_requests': completed_requests,
        'in_progress_count': in_progress_count,
    }
    return render(request, 'main/index.html', context)

@login_required
def profile(request):
   return render(request, 'main/profile.html')


class BBLoginView(LoginView):
   template_name = 'main/login.html'


class BBLogoutView(LoginRequiredMixin, LogoutView):
   template_name = 'main/logout.html'


class ChangeUserInfoView(SuccessMessageMixin, LoginRequiredMixin,UpdateView):
   model = AdvUser
   template_name = 'main/change_user_info.html'
   form_class = ChangeUserInfoForm
   success_url = reverse_lazy('main:profile')
   success_message = 'Личные данные пользователя изменены'


   def dispatch(self, request, *args, **kwargs):
       self.user_id = request.user.pk
       return super().dispatch(request, *args, **kwargs)


   def get_object(self, queryset=None):
       if not queryset:
           queryset = self.get_queryset()
       return get_object_or_404(queryset, pk=self.user_id)


class BBPasswordChangeView(SuccessMessageMixin, LoginRequiredMixin, PasswordChangeView):
   template_name = 'main/password_change.html'
   success_url = reverse_lazy('main:profile')
   success_message = 'Пароль пользователя изменен'



class RegisterUserView(CreateView):
   model = AdvUser
   template_name = 'main/register_user.html'
   form_class = RegisterUserForm
   success_url = reverse_lazy('main:register_done')

class RegisterDoneView(TemplateView):
   template_name = 'main/register_done.html'

class DeleteUserView(LoginRequiredMixin, DeleteView):
   model = AdvUser
   template_name = 'main/delete_user.html'
   success_url = reverse_lazy('main:index')

   def dispatch(self, request, *args, **kwargs):
       self.user_id = request.user.pk
       return super().dispatch(request, *args, **kwargs)

   def post(self, request, *args, **kwargs):
       logout(request)
       messages.add_message(request, messages.SUCCESS, 'Пользователь удален')
       return super().post(request, *args, **kwargs)

   def get_object(self, queryset=None):
       if not queryset:
           queryset = self.get_queryset()
       return get_object_or_404(queryset, pk=self.user_id)

@login_required
def view_requests(request):
    if request.user.is_staff:
        requests = CreateRequest.objects.all()
    else:
        requests = CreateRequest.objects.filter(user=request.user)

    if request.method == 'POST':
        request_id = request.POST.get('request_id')
        request_obj = get_object_or_404(CreateRequest, id=request_id)
        form = ChangeStatusForm(request.POST, request.FILES, instance=request_obj)
        if form.is_valid():
            form.save()
            return redirect('main:view_requests')
    else:
        form = ChangeStatusForm()

    return render(request, 'main/view_requests.html', {'requests': requests, 'form': form})

@login_required
def create_request(request):
    # Проверка на количество заявок со статусом "Новая"
    if CreateRequest.objects.filter(user=request.user, status='new').count() >= 3:
        messages.error(request, 'Вы достигли лимита заявок со статусом "Новая". Пожалуйста, дождитесь, пока одна из ваших заявок не будет обработана.')
        return render(request, 'main/create_request.html', {'form': None})

    if request.method == 'POST':
        form = CreateRequestForm(request.POST, request.FILES)
        if form.is_valid():
            # Проверка на наличие заявки с той же категорией и статусом "Новая"
            category = form.cleaned_data['category']
            if CreateRequest.objects.filter(user=request.user, category=category, status='new').exists():
                messages.error(request, 'У вас уже есть заявка с этой категорией со статусом "Новая".')
                return redirect('main:create_request')

            request_obj = form.save(commit=False)
            request_obj.user = request.user
            request_obj.save()
            return redirect('main:view_requests')
    else:
        form = CreateRequestForm()
    return render(request, 'main/create_request.html', {'form': form})


#метод для удаления заявки
@login_required
def delete_request(request, request_id):
    request_obj = get_object_or_404(CreateRequest, id=request_id)

    # Проверка, что пользователь может удалить заявку
    if request.user != request_obj.user:
        messages.error(request, 'Вы не можете удалить эту заявку.')
        return redirect('main:view_requests')

    # Проверка, что статус заявки не "Принято в работу" или "Выполнено"
    if request_obj.status in ['in_progress', 'completed']:
        messages.error(request, 'Вы не можете удалить заявку со статусом "Принято в работу" или "Выполнено".')
        return redirect('main:view_requests')

    if request.method == 'POST':
        request_obj.delete()
        messages.success(request, 'Заявка успешно удалена.')
        return redirect('main:view_requests')

    return render(request, 'main/delete_request.html', {'request_obj': request_obj})



@require_POST
def check_username(request):
    response_data = {}
    username = request.POST.get("username")
    user = None
    try:
        user = AdvUser.objects.get(username=username)
    except ObjectDoesNotExist:
        pass
    except Exception as e:
        raise e

    if user:
        response_data["exists"] = True
        response_data["message"] = "Пользователь с таким логином уже существует."
    else:
        response_data["exists"] = False

    return JsonResponse(response_data)

@user_passes_test(lambda u: u.is_staff)
@login_required
def change_status(request, request_id):
    request_obj = get_object_or_404(CreateRequest, id=request_id)

    if request_obj.status == 'completed':
        messages.error(request, 'Редактирование заявки с статусом "Выполнено" невозможно.')
        return redirect('main:view_requests')

    if request.method == 'POST':
        form = ChangeStatusForm(request.POST, request.FILES, instance=request_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Заявка успешно отредактирована.')
            return redirect('main:view_requests')
    else:
        form = ChangeStatusForm(instance=request_obj)

    return render(request, 'main/change_status.html', {'form': form, 'request_obj': request_obj})




@login_required
def manage_categories(request):
    if not request.user.is_staff:
        return redirect('main:index')

    categories = Category.objects.all()
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Категория успешно добавлена.')
            return redirect('main:manage_categories')
    else:
        form = CategoryForm()

    return render(request, 'main/manage_categories.html', {'categories': categories, 'form': form})

@login_required
def delete_category(request, category_id):
    if not request.user.is_staff:
        return redirect('main:index')

    category = get_object_or_404(Category, id=category_id)
    CreateRequest.objects.filter(category=category).delete()  # Правильное использование менеджера объектов
    category.delete()
    messages.success(request, 'Категория и все связанные заявки успешно удалены.')
    return redirect('main:manage_categories')

def request_list(request):
    categories = Category.objects.all()
    requests = Request.objects.filter(category__in=categories)
    return render(request, 'main/request_list.html', {'requests': requests})