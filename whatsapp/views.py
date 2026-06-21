import json
import logging
import requests
import os
import re
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.utils import timezone
from transactions.models import Category
from transactions.services import identificar_categoria
from transactions.nlp_parser import interpret_message as parse_message
from transactions.serializers import TransacaoSerializer
from whatsapp.context import get_context, set_context
from whatsapp.gemini import formatar_resumo, interpretar_mensagem, responder_mensagem_livre
from transactions.intent_detector import detect_intent

logger = logging.getLogger(__name__)
User = get_user_model()

# Configs
UAZAPI_URL = os.environ.get("UAZAPI_URL")
UAZAPI_TOKEN = os.environ.get("UAZAPI_TOKEN")
UAZAPI_INSTANCE_NAME = os.environ.get("UAZAPI_INSTANCE_NAME")
EVOLUTION_BOT_KEY = os.environ.get("EVOLUTION_BOT_KEY")

def send_evolution_message(number, text):
    """Envia mensagem ativa para a Uazapi"""
    if not text: return
    base = (UAZAPI_URL or "").strip().rstrip('/')
    token = (UAZAPI_TOKEN or "").strip()
    url = f"{base}/send/text"
    headers = {"token": token, "Content-Type": "application/json"}
    payload = {"number": number, "text": text, "delay": 1200}
    try:
        requests.post(url, json=payload, headers=headers, timeout=10)
    except Exception as e:
        print(f">>> ❌ [ENVIO] Erro: {e}")

@csrf_exempt
def evolution_webhook(request):
    # 1. Segurança
    api_key_received = request.headers.get("apikey") or request.GET.get("apikey")
    if EVOLUTION_BOT_KEY and api_key_received != EVOLUTION_BOT_KEY:
        return HttpResponse("Unauthorized", status=401)
    if request.method != "POST":
        return HttpResponse("Method Not Allowed", status=405)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse("Invalid JSON", status=400)

    # 2. Extração
    message = payload.get("message", {})

    # Ignora mensagens enviadas pelo próprio bot
    if message.get("fromMe") == True:
        return HttpResponse("OK")

    # Uazapi envia número em message.chatid
    number = message.get("chatid", "").replace("@s.whatsapp.net", "")
    if not number:
        return JsonResponse({"status": "ignored", "reason": "no_number"})

    # Resolve o usuário pelo número de WhatsApp
    auth_user = get_auth_user_by_number(number)
    if auth_user is None:
        send_evolution_message(
            number,
            "⚠️ Seu número não está cadastrado no sistema. "
            "Entre em contato com o suporte para criar sua conta."
        )
        return HttpResponse("OK")

    # Uazapi envia texto em message.text
    text = message.get("text") or message.get("content")

    if not text:
        return JsonResponse({"reply": "Nenhuma mensagem válida recebida."})

    # =========================================================================
    # PROCESSAMENTO MULTILINHAS
    # =========================================================================
    if '\n' in text:
        linhas = [l.strip() for l in text.split('\n') if l.strip()]
        if len(linhas) > 1:
            salvas = []
            falhas = []
            for linha in linhas:
                parsed = parse_message(linha)
                if not parsed:
                    parsed = interpretar_mensagem(linha)
                if (parsed and not parsed.get('ambiguo') and not parsed.get('is_correcao')
                        and parsed.get('valor') and parsed.get('tipo')):
                    categoria = None
                    if parsed.get('categoria_texto'):
                        categoria = Category.objects.filter(name__iexact=parsed['categoria_texto']).first()
                    if not categoria:
                        categoria = identificar_categoria(parsed.get('descricao', ''))
                    if not categoria:
                        categoria = Category.objects.filter(name='Outros').first()
                    tipo_banco = 'IN' if parsed['tipo'] == 'R' else 'OUT'
                    transaction_data = {
                        'description': parsed.get('descricao', ''),
                        'value': parsed['valor'],
                        'type': tipo_banco,
                        'date_transaction': timezone.now(),
                        'category': categoria.id if categoria else None,
                    }
                    serializer = TransacaoSerializer(data=transaction_data)
                    if serializer.is_valid():
                        serializer.save(user=auth_user)
                        cat_nome = categoria.name if categoria else 'Outros'
                        salvas.append(f"• R$ {parsed['valor']:.2f} em {cat_nome}")
                    else:
                        falhas.append(linha)
                else:
                    falhas.append(linha)

            if salvas:
                n = len(salvas)
                reply_text = f"✅ {n} transaç{'ões' if n > 1 else 'ão'} salva{'s' if n > 1 else ''}!\n" + "\n".join(salvas)
                if falhas:
                    reply_text += "\n⚠️ Não entendi: " + " | ".join(f'"{f}"' for f in falhas)
            else:
                reply_text = "Não entendi nenhuma das linhas. Tente: 'gastei 50 no mercado'"

            send_evolution_message(number, reply_text)
            return HttpResponse("OK")

    context = get_context(number)
    print(f">>> 🕵️ [EXTRAÇÃO] Texto: '{text}' | Contexto anterior: {context}")

    # =========================================================================
    # RESOLUÇÃO DE AMBIGUIDADE PENDENTE
    # =========================================================================
    if context and context.get("aguardando_confirmacao") and context.get("ultimo_parsed"):
        parsed_reescrito = parse_message(text)
        print(f">>> 🔄 [AMBIGUIDADE] Tentando resolver com: '{text}' | Reescrito: {parsed_reescrito}")
        parsed_final = parsed_reescrito if (parsed_reescrito and not parsed_reescrito.get("ambiguo")) else None

        if parsed_final is None:
            valor_anterior = context["ultimo_parsed"].get("valor")
            tem_valor_no_texto = bool(re.search(r'\b\d+(?:[.,]\d+)?\b', text))
            if valor_anterior is not None and not tem_valor_no_texto:
                if parsed_reescrito is None:
                    texto_tentativa = f"{text} {valor_anterior}"
                    print(f">>> 🔄 [AMBIGUIDADE] Segunda estratégia: tentando parsear '{texto_tentativa}'")
                    parsed_tentativa = parse_message(texto_tentativa)
                    if parsed_tentativa and not parsed_tentativa.get("ambiguo"):
                        parsed_final = parsed_tentativa
                        print(f">>> 🔄 [AMBIGUIDADE] Segunda estratégia: sucesso | Resultado: {parsed_final}")
                else:
                    parsed_mesclado = {**parsed_reescrito, "valor": valor_anterior}
                    if parsed_mesclado.get("tipo") and parsed_mesclado.get("valor") is not None:
                        parsed_final = parsed_mesclado
                        print(f">>> 🔄 [AMBIGUIDADE] Segunda estratégia: mescla direta | Mesclado: {parsed_final}")

        if parsed_final:
            parsed_data = parsed_final

            categoria = None
            if parsed_data.get("categoria_texto"):
                categoria = Category.objects.filter(name__iexact=parsed_data["categoria_texto"]).first()
            if not categoria:
                categoria = identificar_categoria(parsed_data.get("descricao", ""))
            if not categoria:
                categoria = Category.objects.filter(name="Outros").first()

            tipo_banco = "IN" if parsed_data.get("tipo") == "R" else "OUT"
            transaction_data = {
                "description": parsed_data.get("descricao", ""),
                "value": parsed_data["valor"],
                "type": tipo_banco,
                "date_transaction": timezone.now(),
                "category": categoria.id if categoria else None,
            }
            serializer = TransacaoSerializer(data=transaction_data)
            if serializer.is_valid():
                serializer.save(user=auth_user)
                cat_nome = categoria.name if categoria else "Outros"
                set_context(number, {
                    "ultimo_texto": text,
                    "ultimo_parsed": parsed_data,
                    "timestamp": timezone.now().isoformat(),
                })
                send_evolution_message(number, f"✅ Salvo em *{cat_nome}*! \nValor: R$ {parsed_data['valor']:.2f}")
                return HttpResponse("OK")

    # =========================================================================
    # COMPLEMENTAÇÃO DE CONTEXTO
    # =========================================================================
    match_valor = re.search(r'\b(\d+(?:[.,]\d+)?)\b', text)
    is_mensagem_so_valor = bool(match_valor and re.fullmatch(
        r'R?\$?\s*\d+(?:[.,]\d+)?\s*(reais?)?\s*', text.strip(), re.IGNORECASE
    ))

    if context and is_mensagem_so_valor and context.get("ultimo_parsed"):
        novo_valor = float(match_valor.group(1).replace(",", "."))
        parsed_complementado = {**context["ultimo_parsed"], "valor": novo_valor}
        print(f">>> 🔗 [CONTEXTO] Complementando com valor {novo_valor} | Base: {context['ultimo_parsed']}")

        categoria = None
        if parsed_complementado.get("categoria_texto"):
            categoria = Category.objects.filter(name__iexact=parsed_complementado["categoria_texto"]).first()
        if not categoria:
            categoria = identificar_categoria(parsed_complementado.get("descricao", ""))
        if not categoria:
            categoria = Category.objects.filter(name="Outros").first()

        tipo_banco = "IN" if parsed_complementado.get("tipo") == "R" else "OUT"
        transaction_data = {
            "description": parsed_complementado.get("descricao", ""),
            "value": novo_valor,
            "type": tipo_banco,
            "date_transaction": timezone.now(),
            "category": categoria.id if categoria else None,
        }
        serializer = TransacaoSerializer(data=transaction_data)
        if serializer.is_valid():
            serializer.save(user=auth_user)
            cat_nome = categoria.name if categoria else "Outros"
            set_context(number, {
                "ultimo_texto": text,
                "ultimo_parsed": parsed_complementado,
                "timestamp": timezone.now().isoformat(),
            })
            send_evolution_message(number, f"✅ Salvo em *{cat_nome}*! \nValor: R$ {novo_valor:.2f}")
            return HttpResponse("OK")

    # =========================================================================
    # DETECÇÃO DE INTENÇÃO (CONSULTAS)
    # =========================================================================
    intent = detect_intent(text)
    tipo_consulta = intent["tipo"] if intent else None
    extra_params_dict = intent["extra_params"] if intent else {}
    extra_params = "".join(f"&{k}={v}" for k, v in extra_params_dict.items())

    # --- EXECUÇÃO DA CONSULTA ---
    if tipo_consulta:
        print(f">>>🔍 [CONSULTA] Tipo: {tipo_consulta} | Params: {extra_params}")
        try:
            base_url = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")

            if tipo_consulta == "insights":
                response = requests.get(f"{base_url}/api/insights/?user_id={auth_user.id}", timeout=5)
                dados = response.json()
                if response.status_code == 200:
                    reply_text = formatar_resumo(dados)
                    if not reply_text:
                        saldo = dados.get("saldo_atual", 0.0)
                        receitas = dados.get("total_receitas_mes", 0.0)
                        despesas = dados.get("total_despesas_mes", 0.0)
                        lider = dados.get("categoria_lider") or "—"
                        comparativo = dados.get("comparativo_mes_anterior")
                        variacao = f"{comparativo:+.1f}%" if comparativo is not None else "sem dados"
                        reply_text = (
                            f"📊 *Resumo financeiro:*\n"
                            f"💰 Saldo: R$ {saldo:.2f}\n"
                            f"📈 Receitas do mês: R$ {receitas:.2f}\n"
                            f"📉 Despesas do mês: R$ {despesas:.2f}\n"
                            f"🏆 Maior gasto: {lider}\n"
                            f"📅 Variação vs mês anterior: {variacao}"
                        )
                else:
                    reply_text = f"⚠️ Erro ao buscar insights: {dados.get('error')}"
                send_evolution_message(number, reply_text)
                return HttpResponse("OK")

            url_api = f"{base_url}/api/consulta/?tipo={tipo_consulta}{extra_params}&user_id={auth_user.id}"
            response = requests.get(url_api, timeout=5)
            dados = response.json()

            if response.status_code == 200:
                if tipo_consulta == "filtro_combinado":
                    valor = dados.get("valor", 0.0)
                    cat_nome = dados.get("categoria", "essa categoria").capitalize()
                    periodo_txt = "nesta semana" if extra_params_dict.get("periodo") == "semana" else "neste mês"
                    reply_text = f"🔎 Gastos com *{cat_nome}* {periodo_txt}: R$ {valor:.2f}"

                elif tipo_consulta == "categorias":
                    lista = dados.get("dados", [])
                    if not lista:
                        reply_text = "🤷 Sem gastos por categoria no período."
                    else:
                        items = [f"▫️ {i['categoria']}: R$ {i['valor']:.2f}" for i in lista]
                        reply_text = "📊 *Gastos por Categoria:*\n" + "\n".join(items)

                elif tipo_consulta == "historico":
                    lista = dados.get("dados", [])
                    if not lista:
                        reply_text = "🤷 Nenhuma transação encontrada."
                    else:
                        linhas = []
                        for t in lista:
                            sinal = "📈" if t["tipo"] == "IN" else "📉"
                            linhas.append(
                                f"{sinal} {t['data'][:10].split('-')[2]}/{t['data'][:10].split('-')[1]}/{t['data'][:10].split('-')[0]} — {t['categoria']}: R$ {t['valor']:.2f}"
                            )
                        reply_text = "🧾 *Últimas transações:*\n" + "\n".join(linhas)

                else:
                    valor = dados.get("valor", 0.0)
                    titulos = {
                        "saldo": "💰 *Saldo Atual:*",
                        "hoje": "📅 *Hoje:*",
                        "semana": "🗓️ *Semana:*",
                        "despesas": "📉 *Mês:*",
                        "mes_passado": "📉 *Mês passado:*",
                        "receitas": "📈 *Receitas:*",
                        "receitas_semana": "🤑 *Receitas (Semana):*",
                    }
                    reply_text = f"{titulos.get(tipo_consulta, 'Consulta:')} R$ {valor:.2f}"
            else:
                reply_text = f"⚠️ Erro na API: {dados.get('error')}"

        except Exception as e:
            print(f">>> ❌ Erro: {e}")
            reply_text = "Erro ao consultar dados."

        send_evolution_message(number, reply_text)
        return HttpResponse("OK")

    # =========================================================================
    # LÓGICA DE CADASTRO (CRIAR TRANSAÇÃO)
    # =========================================================================

    parsed_data = parse_message(text)
    reply_text = ""

    if parsed_data:
        print(f">>> 💰 [PARSER] Entendido: {parsed_data}")

        # ---- CORREÇÃO: substitui a última transação pelo valor corrigido ----
        if parsed_data.get("is_correcao"):
            from transactions.models import Transacao
            from django.db.models.deletion import ProtectedError
            ultima = Transacao.objects.filter(user=auth_user).first()
            if not ultima:
                reply_text = "Não há transação anterior para corrigir."
            else:
                novo_valor = parsed_data["valor"]
                nova = Transacao(
                    user=ultima.user,
                    value=novo_valor,
                    type=ultima.type,
                    description=ultima.description,
                    category=ultima.category,
                    date_transaction=ultima.date_transaction,
                )
                try:
                    ultima.delete()
                    nova.save()
                    reply_text = f"✅ Corrigi para R$ {novo_valor:.2f}!"
                except ProtectedError:
                    reply_text = (
                        "Não foi possível corrigir: a transação está vinculada "
                        "a uma mensagem protegida. Entre em contato com o suporte."
                    )
            send_evolution_message(number, reply_text)
            return HttpResponse("OK")

        # ---- AMBIGUIDADE (RF08): pede clarificação em vez de salvar ----
        if parsed_data.get("ambiguo"):
            motivo = parsed_data.get("motivo_ambiguidade") or "não entendi bem"
            reply_text = f"🤔 Hmm, {motivo}. Pode tentar de novo? Ex: 'gastei 50 no mercado' ou 'recebi 1500 de salário'"
            send_evolution_message(number, reply_text)
            set_context(number, {
                "aguardando_confirmacao": True,
                "ultimo_texto": text,
                "ultimo_parsed": parsed_data,
                "timestamp": timezone.now().isoformat(),
            })
            return HttpResponse("OK")

        categoria = None
        if parsed_data.get("categoria_texto"):
            categoria = Category.objects.filter(name__iexact=parsed_data["categoria_texto"]).first()
        if not categoria:
            categoria = identificar_categoria(parsed_data["descricao"])
        if not categoria:
            categoria = Category.objects.filter(name="Outros").first()

        tipo_banco = "IN" if parsed_data["tipo"] == "R" else "OUT"

        transaction_data = {
            "description": parsed_data["descricao"],
            "value": parsed_data["valor"],
            "type": tipo_banco,
            "date_transaction": timezone.now(),
            "category": categoria.id if categoria else None
        }

        serializer = TransacaoSerializer(data=transaction_data)

        if serializer.is_valid():
            serializer.save(user=auth_user)
            cat_nome = categoria.name if categoria else "Outros"
            reply_text = f"✅ Salvo em *{cat_nome}*! \nValor: R$ {parsed_data['valor']:.2f}"
            set_context(number, {
                "ultimo_texto": text,
                "ultimo_parsed": parsed_data,
                "timestamp": timezone.now().isoformat(),
            })
        else:
            reply_text = "Erro ao salvar. Verifique o formato."
            print(f">>> ❌ [SERIALIZER] Erros: {serializer.errors}")
    else:
        # Fallback Gemini: tenta interpretar o que o nlp_parser não entendeu
        gemini_parsed = interpretar_mensagem(text)
        if gemini_parsed:
            print(f">>> 🤖 [GEMINI] Interpretado: {gemini_parsed}")
            categoria = None
            if gemini_parsed.get("categoria_texto"):
                categoria = Category.objects.filter(name__iexact=gemini_parsed["categoria_texto"]).first()
            if not categoria:
                categoria = identificar_categoria(gemini_parsed.get("descricao", ""))
            if not categoria:
                categoria = Category.objects.filter(name="Outros").first()

            tipo_banco = "IN" if gemini_parsed["tipo"] == "R" else "OUT"
            transaction_data = {
                "description": gemini_parsed.get("descricao", ""),
                "value": gemini_parsed["valor"],
                "type": tipo_banco,
                "date_transaction": timezone.now(),
                "category": categoria.id if categoria else None,
            }
            serializer = TransacaoSerializer(data=transaction_data)
            if serializer.is_valid():
                serializer.save(user=auth_user)
                cat_nome = categoria.name if categoria else "Outros"
                set_context(number, {
                    "ultimo_texto": text,
                    "ultimo_parsed": gemini_parsed,
                    "timestamp": timezone.now().isoformat(),
                })
                reply_text = f"✅ Salvo em *{cat_nome}*! \nValor: R$ {gemini_parsed['valor']:.2f}"
            else:
                reply_text = "Não entendi sua mensagem. Tente: 'gastei 50 no mercado' ou 'quanto gastei esse mês?'"
        else:
            dados_financeiros = None
            try:
                base_url = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
                resp_insights = requests.get(f"{base_url}/api/insights/?user_id={auth_user.id}", timeout=5)
                if resp_insights.status_code == 200:
                    ins = resp_insights.json()
                    dados_financeiros = {
                        "saldo": ins.get("saldo_atual", 0.0),
                        "total_receitas": ins.get("total_receitas_mes", 0.0),
                        "total_despesas": ins.get("total_despesas_mes", 0.0),
                        "categoria_lider": ins.get("categoria_lider"),
                    }
            except Exception:
                pass
            reply_text = responder_mensagem_livre(text, dados_financeiros) or "Não entendi sua mensagem. Tente: 'gastei 50 no mercado' ou 'quanto gastei esse mês?'"

    if reply_text:
        send_evolution_message(number, reply_text)

    return HttpResponse("OK")


def get_auth_user_by_number(number):
    """Obtém ou cria o usuário auth.User a partir do telefone normalizado do WhatsApp."""
    if not number:
        return None
    clean_number = "".join(filter(str.isdigit, number))
    
    from users.models import User as UserProfile
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # 1. Obtém ou cria o perfil correspondente ao número
    profile, created = UserProfile.objects.get_or_create(
        phone_number=clean_number,
        defaults={
            "name": "Usuário WhatsApp",
            "time_zone": "America/Sao_Paulo",
            "locale": "pt_BR",
        }
    )
    
    # 2. Se o perfil não tem auth_user, cria um temporário
    if profile.auth_user is None:
        temp_username = f"temp_{clean_number}"
        auth_user, user_created = User.objects.get_or_create(
            username=temp_username,
            defaults={
                "first_name": "Usuário WhatsApp",
                "email": f"{clean_number}@temp.whatsapp.com"
            }
        )
        if user_created:
            import secrets
            auth_user.set_password(secrets.token_urlsafe(16))
            auth_user.save()
            
        profile.auth_user = auth_user
        profile.save()
        
    return profile.auth_user