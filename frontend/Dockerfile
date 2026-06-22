FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

# 정적 사이트 생성 → /app/dist (nginx 게이트웨이가 이걸 서빙)
RUN npm run generate

# 정적 아티팩트만 배출하는 단계 — 실제 런타임은 nginx 컨테이너가 담당
FROM scratch AS artifact
COPY --from=builder /app/dist /dist
