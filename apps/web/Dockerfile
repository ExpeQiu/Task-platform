FROM node:20-alpine AS base

WORKDIR /app/apps/web

COPY apps/web/package.json apps/web/package-lock.json* ./
RUN npm install

COPY apps/web/ .

RUN npm run build

EXPOSE 3000
CMD ["npm", "start"]
