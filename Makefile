.PHONY: setup-multiarch-builder
setup-multiarch-builder:
	docker buildx create --name multiarch --driver docker-container --use --driver-opt network=host

.PHONY: build-default-image-builder-image
build-default-image-builder-image: export DEFAULT_BUILDER_BASE_IMAGE ?= docker.io/thomasjpfan/default-image-builder-base:0.0.3
build-default-image-builder-image:
	docker image build --builder multiarch \
		-f experiments/Dockerfile.default-image-builder \
		--platform linux/arm64,linux/amd64 \
		-t ${DEFAULT_BUILDER_BASE_IMAGE} \
		--push .
