from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from backyardflow.roles import role_required
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from .models import Table, TableArea, Reservation
from .forms import TableForm, TableAreaForm, ReservationForm


@role_required('tables')
def table_map(request):
    areas = TableArea.objects.filter(active=True).prefetch_related('tables')
    tables_no_area = Table.objects.filter(area__isnull=True, active=True)
    all_tables = Table.objects.filter(active=True)

    stats = {
        'free': all_tables.filter(status='FREE').count(),
        'occupied': all_tables.filter(status='OCCUPIED').count(),
        'reserved': all_tables.filter(status='RESERVED').count(),
        'cleaning': all_tables.filter(status='CLEANING').count(),
        'total': all_tables.count(),
    }

    today = timezone.now().date()
    today_reservations = Reservation.objects.filter(
        date=today,
        status__in=['PENDING', 'CONFIRMED']
    ).select_related('table').order_by('time')

    context = {
        'areas': areas,
        'tables_no_area': tables_no_area,
        'stats': stats,
        'today_reservations': today_reservations,
    }
    return render(request, 'tables/table_map.html', context)


class TableCreateView(LoginRequiredMixin, CreateView):
    model = Table
    form_class = TableForm
    template_name = 'tables/table_form.html'
    success_url = reverse_lazy('tables:table_map')

    def form_valid(self, form):
        messages.success(self.request, 'Mesa creada exitosamente.')
        return super().form_valid(form)


class TableUpdateView(LoginRequiredMixin, UpdateView):
    model = Table
    form_class = TableForm
    template_name = 'tables/table_form.html'
    success_url = reverse_lazy('tables:table_map')

    def form_valid(self, form):
        messages.success(self.request, 'Mesa actualizada.')
        return super().form_valid(form)


class TableDeleteView(LoginRequiredMixin, DeleteView):
    model = Table
    template_name = 'tables/table_confirm_delete.html'
    success_url = reverse_lazy('tables:table_map')

    def form_valid(self, form):
        self.object.active = False
        self.object.save()
        messages.success(self.request, 'Mesa desactivada.')
        return redirect(self.success_url)


class TableAreaCreateView(LoginRequiredMixin, CreateView):
    model = TableArea
    form_class = TableAreaForm
    template_name = 'tables/area_form.html'
    success_url = reverse_lazy('tables:table_map')

    def form_valid(self, form):
        messages.success(self.request, 'Area creada exitosamente.')
        return super().form_valid(form)


class TableAreaUpdateView(LoginRequiredMixin, UpdateView):
    model = TableArea
    form_class = TableAreaForm
    template_name = 'tables/area_form.html'
    success_url = reverse_lazy('tables:table_map')

    def form_valid(self, form):
        messages.success(self.request, 'Area actualizada.')
        return super().form_valid(form)


@role_required('tables')
def update_table_status(request, pk):
    if request.method == 'POST':
        table = get_object_or_404(Table, pk=pk)
        new_status = request.POST.get('status')
        valid_statuses = [s[0] for s in Table.STATUS_CHOICES]
        if new_status in valid_statuses:
            table.status = new_status
            table.save()
            return JsonResponse({
                'success': True,
                'status': table.status,
                'status_display': table.get_status_display(),
                'status_color': table.status_color
            })
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)


class ReservationListView(LoginRequiredMixin, ListView):
    model = Reservation
    template_name = 'tables/reservation_list.html'
    context_object_name = 'reservations'
    paginate_by = 20

    def get_queryset(self):
        queryset = Reservation.objects.select_related('table').order_by('-date', '-time')
        date_filter = self.request.GET.get('date')
        status = self.request.GET.get('status')
        if date_filter:
            queryset = queryset.filter(date=date_filter)
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['statuses'] = Reservation.STATUS_CHOICES
        ctx['today'] = timezone.now().date()
        return ctx


class ReservationCreateView(LoginRequiredMixin, CreateView):
    model = Reservation
    form_class = ReservationForm
    template_name = 'tables/reservation_form.html'
    success_url = reverse_lazy('tables:reservation_list')

    def form_valid(self, form):
        messages.success(self.request, 'Reserva creada exitosamente.')
        return super().form_valid(form)


class ReservationUpdateView(LoginRequiredMixin, UpdateView):
    model = Reservation
    form_class = ReservationForm
    template_name = 'tables/reservation_form.html'
    success_url = reverse_lazy('tables:reservation_list')

    def form_valid(self, form):
        messages.success(self.request, 'Reserva actualizada.')
        return super().form_valid(form)


@role_required('tables')
def generate_table_qr(request, pk):
    table = get_object_or_404(Table, pk=pk)
    result = table.generate_qr()
    if result:
        messages.success(request, f'QR generado para Mesa {table.number}.')
    else:
        messages.error(request, 'Error al generar el QR. Asegurese de tener instalado qrcode.')
    return redirect('tables:table_map')
