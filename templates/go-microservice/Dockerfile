FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /server .

FROM alpine:3.19
WORKDIR /app
COPY --from=builder /server .
EXPOSE 8080
CMD ["./server"]
