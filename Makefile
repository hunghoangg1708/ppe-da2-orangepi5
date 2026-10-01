PYTHON ?= .venv/bin/python
CONFIG ?= ai/automation/configs/sfchd_5class_yolov8n_baseline.yaml

.PHONY: help check test prepare-data train export-npu benchmark-npu leaderboard

help:
	@echo "make test                       - test class mapping and fixed split"
	@echo "make check                      - check Python dependencies"
	@echo "make prepare-data               - create the SFCHD five-class dataset"
	@echo "make train [CONFIG=path]        - train and evaluate a baseline"
	@echo "make export-npu RUN=<run_id>    - export a trained checkpoint to RKNN"
	@echo "make benchmark-npu RUN=<run_id> DEVICE=<ip:port> [CORE_MASK=AUTO]"
	@echo "make leaderboard               - view the five-class results"

check:
	$(PYTHON) -c "import torch, numpy, ultralytics; from rknn.api import RKNN; print('torch', torch.__version__, 'cuda', torch.cuda.is_available()); print('numpy', numpy.__version__); print('RKNN OK')"

test:
	$(PYTHON) -m unittest discover -s tests -v

prepare-data:
	$(PYTHON) scripts/data/prepare_sfchd_5class.py

train:
	$(PYTHON) -m ai.automation.run $(CONFIG)

export-npu:
	$(PYTHON) -m ai.automation.export_npu $(RUN)

benchmark-npu:
	$(PYTHON) -m ai.automation.benchmark_npu $(RUN) $(DEVICE) --core-mask $(or $(CORE_MASK),AUTO)

leaderboard:
	cat ai/automation/leaderboards/sfchd_5class.csv
