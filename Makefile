all: lint build test

.PHONY: clean
clean:
	$(RM) zeyple

build: *.go
	go build -v

test: *.go
	go test -v ./...

.PHONY: lint
lint:
	golangci-lint run
