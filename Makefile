.PHONY: help manifest bindings smoke test contract-ci xlang
help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-10s %s\n",$$1,$$2}'
manifest: ## Print the connector manifest
	urirun-kvm manifest
bindings: ## Print urirun bindings
	urirun-kvm bindings
smoke: ## bindings -> urirun connectors smoke (dry-run, headless)
	urirun-kvm bindings | urirun connectors smoke - \
	  --run 'kvm://host/screen/query/capture' --payload '{"output":"shot.png"}' \
	  --allow 'kvm://*' --name kvm
test: ## Install editable + smoke
	pip install -e . && python3 -m pytest -q && $(MAKE) smoke
contract-ci: ## 7-gate: conformance + composition + shape-lint + IPC + polyglot + driver + transport (URIRUN_CONTRACT_CHECK=1)
	@bash ci/contract_ci.sh
xlang: ## Polyglot proof only (py·js·go): 3×3 matrix + external driver + transport swap
	@bash xlang/run.sh && bash xlang/driver.sh && bash xlang/transport_swap.sh
