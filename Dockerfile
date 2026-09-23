FROM node:22-alpine AS frontend
WORKDIR /web
COPY package.json vite.config.js index.html ./
COPY src ./src
RUN npm install && npm run build

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
COPY --from=frontend /web/dist ./dist
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn","gateway:app","--host","0.0.0.0","--port","8000"]