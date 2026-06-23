# Docker Guide

Docker files:

- docker-compose.yml
- backend/Dockerfile
- backend/.dockerignore
- frontend/Dockerfile
- frontend/nginx.conf
- frontend/.dockerignore

Run:

docker compose up --build

Frontend:
http://localhost:5173

Backend health:
http://localhost:20000/api/v1/customer-portal/health

ML health:
http://localhost:20000/api/v1/ml/health

AI RAG health:
http://localhost:20000/api/v1/ai-rag/health

