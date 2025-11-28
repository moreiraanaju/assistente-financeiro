
# Usando uma imagem base oficial do Python
FROM python:3.12-slim


ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Definindo o diretório de trabalho dentro do container
WORKDIR /app

# Copiando o arquivo de dependências
COPY requirements.txt /app/
RUN pip install  --no-cache-dir -r requirements.txt

# Copiando todo o código para dentro do container
COPY . /app


# Expoe a porta 800 (a mesma do docker-compose)
EXPOSE 8000

# Conferir se isso tá correto (duas linhas )
RUN python manage.py collectstatic --noinput || true

CMD bash -lc "python manage.py migrate --noinput && python manage.py collectstatic --noinput || true && gunicorn core.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 --timeout 120"