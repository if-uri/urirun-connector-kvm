.PHONY: help manifest bindings smoke test
help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-10s %s\n",$$1,$$2}'
manifest: ## Print the connector manifest
	urirun-connector-kvm manifest
bindings: ## Print urirun bindings
	urirun-connector-kvm bindings
smoke: ## bindings -> urirun connectors smoke (dry-run, headless)
	urirun-connector-kvm bindings | urirun connectors smoke - \
	  --run 'kvm://host/screen/query/capture' --payload '{"output":"shot.png"}' \
	  --allow 'kvm://*' --name kvm
test: ## Install editable + smoke
	pip install -e . && python3 -m pytest -q && $(MAKE) smoke
