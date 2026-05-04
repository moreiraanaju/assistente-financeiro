from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum, Q
import calendar
from datetime import timedelta
from transactions.models import Transacao

def subtract_months(dt, months):
    month = dt.month - 1 - months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)

def get_date_range(periodo, now=None):
    if not now:
        now = timezone.localtime(timezone.now())
        
    if periodo == 'dia':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        prev_start = start - timedelta(days=1)
        prev_end = end - timedelta(days=1)
    elif periodo == 'semana':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=6)
        end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        prev_start = start - timedelta(days=7)
        prev_end = end - timedelta(days=7)
    elif periodo == 'trimestre':
        start = subtract_months(now, 3).replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        prev_start = subtract_months(start, 3)
        prev_end = subtract_months(end, 3)
    elif periodo == 'ano':
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
        prev_start = subtract_months(start, 12)
        prev_end = subtract_months(end, 12)
    else: # mes
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month = subtract_months(start, -1)
        end = next_month - timedelta(seconds=1)
        prev_end = start - timedelta(seconds=1)
        
    return start, end, prev_start, prev_end

def get_date_range_cards(periodo, now=None):
    if not now:
        now = timezone.localtime(timezone.now())
        
    end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    if periodo == 'dia':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        prev_start = start - timedelta(days=1)
        prev_end = end - timedelta(days=1)
    elif periodo == 'semana':
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        prev_start = start - timedelta(days=7)
        prev_end = start - timedelta(seconds=1)
    elif periodo == 'trimestre':
        start = subtract_months(now, 3).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_start = subtract_months(start, 3)
        prev_end = start - timedelta(seconds=1)
    elif periodo == 'ano':
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_start = subtract_months(start, 12)
        prev_end = start - timedelta(seconds=1)
    else: # mes
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_start = subtract_months(start, 1)
        prev_end = start - timedelta(seconds=1)
        
    return start, end, prev_start, prev_end

@login_required
def dashboard_index(request):
    context = {}
    return render(request, 'dashboard/index.html', context)

@login_required
def resumo_dashboard(request):
    periodo_cards = request.GET.get('periodo_cards', 'mes')
    periodo_graficos = request.GET.get('periodo_graficos', 'mes')
    
    now = timezone.localtime(timezone.now())
    start_c, end_c, prev_start_c, prev_end_c = get_date_range_cards(periodo_cards, now)
    start_g, end_g, _, _ = get_date_range(periodo_graficos, now)
    
    # 1. CARDS
    transacoes_cards = Transacao.objects.filter(
        user=request.user,
        date_transaction__gte=start_c,
        date_transaction__lte=end_c
    )
    
    totais = transacoes_cards.aggregate(
        receitas=Sum('value', filter=Q(type='IN')),
        despesas=Sum('value', filter=Q(type='OUT'))
    )
    total_receitas = float(totais['receitas'] or 0.0)
    total_despesas = float(totais['despesas'] or 0.0)
    saldo = float(total_receitas - total_despesas)
    
    despesas_anterior = Transacao.objects.filter(
        user=request.user,
        type='OUT',
        date_transaction__gte=prev_start_c,
        date_transaction__lte=prev_end_c
    ).aggregate(total=Sum('value'))['total'] or 0.0
    
    variacao_mes_anterior = float(total_despesas - float(despesas_anterior))
    
    gastos_cat_cards = transacoes_cards.filter(type='OUT', category__isnull=False).values(
        'category__name'
    ).annotate(total=Sum('value')).order_by('-total')
    
    if gastos_cat_cards:
        categoria_lider = {
            "nome": gastos_cat_cards[0]['category__name'],
            "total": float(gastos_cat_cards[0]['total'])
        }
    else:
        categoria_lider = {"nome": "Nenhuma", "total": 0.0}
        
    # 2. GRÁFICOS
    transacoes_graficos = Transacao.objects.filter(
        user=request.user,
        date_transaction__gte=start_g,
        date_transaction__lte=end_g
    )
    
    gastos_cat_graficos = transacoes_graficos.filter(type='OUT', category__isnull=False).values(
        'category__name'
    ).annotate(total=Sum('value')).order_by('-total')
    
    gastos_por_categoria = [
        {"categoria": g['category__name'], "total": float(g['total'])}
        for g in gastos_cat_graficos
    ]
    
    # Evolução Semanal (Bins)
    points = []
    duration = end_g - start_g
    
    if periodo_graficos == 'dia': num_points = 24
    elif periodo_graficos == 'semana': num_points = 7
    elif periodo_graficos == 'mes': num_points = 4
    elif periodo_graficos == 'trimestre': num_points = 12
    elif periodo_graficos == 'ano': num_points = 12
    else: num_points = 4
    
    bin_duration = duration / num_points
    
    for i in range(num_points):
        bin_start = start_g + i * bin_duration
        bin_end = start_g + (i + 1) * bin_duration
        
        if periodo_graficos == 'dia':
            label = bin_start.strftime('%H:%M')
        elif periodo_graficos == 'semana':
            # pt-br translation approximation
            dias = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
            label = dias[bin_start.weekday()]
        elif periodo_graficos in ['mes', 'trimestre']:
            label = f"Semana {i+1}" if periodo_graficos == 'mes' else f"Sem {i+1}"
        elif periodo_graficos == 'ano':
            meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
            label = meses[bin_start.month - 1]
        else:
            label = f"Ponto {i+1}"
            
        points.append({
            'start': bin_start,
            'end': bin_end,
            'receitas': 0.0,
            'despesas': 0.0,
            'label': label
        })
        
    for t in transacoes_graficos.values('date_transaction', 'type', 'value'):
        t_date = timezone.localtime(t['date_transaction'])
        # Achar o bin correspondente
        bin_index = int((t_date - start_g).total_seconds() / bin_duration.total_seconds())
        if bin_index >= num_points:
            bin_index = num_points - 1
        elif bin_index < 0:
            bin_index = 0
            
        if t['type'] == 'IN':
            points[bin_index]['receitas'] += float(t['value'])
        elif t['type'] == 'OUT':
            points[bin_index]['despesas'] += float(t['value'])
            
    evolucao_semanal = [
        {"label": p['label'], "receitas": p['receitas'], "despesas": p['despesas']}
        for p in points
    ]
    
    return JsonResponse({
        "saldo": saldo,
        "total_receitas": total_receitas,
        "total_despesas": total_despesas,
        "categoria_lider": categoria_lider,
        "variacao_mes_anterior": variacao_mes_anterior,
        "evolucao_semanal": evolucao_semanal,
        "gastos_por_categoria": gastos_por_categoria
    })
