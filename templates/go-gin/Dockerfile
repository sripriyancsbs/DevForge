FROM golang:1.22-alpine AS builder

WORKDIR /app

COPY go.mod ./
COPY go.sum* ./
RUN go mod download || true

COPY . .

RUN go mod tidy && CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o /app/server .

FROM alpine:3.19

RUN apk --no-cache add ca-certificates curl

WORKDIR /app
COPY --from=builder /app/server .

EXPOSE {{PORT}}

CMD ["./server"]
