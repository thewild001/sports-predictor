FROM mcr.microsoft.com/playwright:v1.56.1-noble
WORKDIR /app
COPY package*.json ./
RUN npm install --omit=dev
COPY tsconfig.json ./
COPY src ./src
RUN npm install --no-save typescript @types/node && npx tsc -p tsconfig.json
ENV NODE_ENV=production
EXPOSE 8787
CMD ["npm", "start"]
