# DevDesk Build System
PYTHON = .venv/bin/python3
PYINSTALLER = .venv/bin/pyinstaller

# Hidden imports required by Uvicorn dynamic loader
UVICORN_FLAGS = --hidden-import=uvicorn.loops.auto \
                --hidden-import=uvicorn.protocols.http.auto \
                --hidden-import=uvicorn.lifespan.on

.PHONY: all setup build clean install

all: build

$(PYINSTALLER):
	@echo "--> Virtual environment or pyinstaller not found. Running setup..."
	@$(MAKE) setup

setup:
	@echo "--> Creating virtual environment and installing dependencies..."
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	@echo "\n=== Environment ready! Activate with: source .venv/bin/activate ==="

build: build-vault build-netwatch build-workpulse
	@echo "\n=== All 3 DevDesk binaries built successfully in ./dist/ ==="

build-vault: $(PYINSTALLER)
	@echo "--> Building vault binary..."
	$(PYINSTALLER) --onefile --name vault --paths=. $(UVICORN_FLAGS) snippetvault/src/main.py

build-netwatch: $(PYINSTALLER)
	@echo "--> Building netwatch binary..."
	$(PYINSTALLER) --onefile --name netwatch --paths=. $(UVICORN_FLAGS) netwatch/src/main.py

build-workpulse: $(PYINSTALLER)
	@echo "--> Building workpulse binary..."
	$(PYINSTALLER) --onefile --name workpulse --paths=. workpulse/src/main.py

install:
	@echo "--> Installing binaries to ~/.local/bin/..."
	mkdir -p ~/.local/bin
	cp dist/vault ~/.local/bin/
	cp dist/netwatch ~/.local/bin/
	cp dist/workpulse ~/.local/bin/
	@echo "Installed! Ensure ~/.local/bin is in your PATH."

clean:
	@echo "--> Cleaning build artifacts..."
	rm -rf build dist *.spec