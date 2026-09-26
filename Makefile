# =====================================================================
# RAG-ПАКЕТ АССИСТЕНТА «ШУЛЬБЕРТ» (АВТОМАТИЗАЦИЯ ДЕПЛОЯ УТИЛИТ)
# =====================================================================

.PHONY: all venv git git_local git_remote

PROJECT_NAME = schulbert
WHOAMI       = $(shell whoami)
SHARE_DIR    = /usr/share/$(PROJECT_NAME)/rag-pipeline
VENV_DIR     = $(SHARE_DIR)/.venv
DOTENV_FN    = $(SHARE_DIR)/.env
MUSIC_DIR    = $(HOME)/Музыка

REQUIREMENTS_SRC = requirements.txt
REQUIREMENTS_DST = $(SHARE_DIR)/$(REQUIREMENTS_SRC)

# Главная цель сборки
all: venv
	@echo "📦 [Деплой RAG]: Копирование утилит в системную директорию..."
	cp m3u2yaml.py $(SHARE_DIR)/
	cp m3u2db.py $(SHARE_DIR)/
	cp refresh-embeddings.py $(SHARE_DIR)/
	cp extract_tags.py $(SHARE_DIR)/
	
	@echo "📦 [Деплой RAG]: Генерация локальных алиасов в $(MUSIC_DIR)/.bash_music..."
	mkdir -p $(MUSIC_DIR)
	cp .bash_music $(MUSIC_DIR)
	@echo "alias m3u2yaml='$(VENV_DIR)/bin/python3 $(SHARE_DIR)/m3u2yaml.py'"                       >> $(MUSIC_DIR)/.bash_music
	@echo "alias m3u2db='$(VENV_DIR)/bin/python3 $(SHARE_DIR)/m3u2db.py'"                           >> $(MUSIC_DIR)/.bash_music
	@echo "alias refresh-embeddings='$(VENV_DIR)/bin/python3 $(SHARE_DIR)/refresh-embeddings.py'"   >> $(MUSIC_DIR)/.bash_music
	@echo "🎉 Успех! Изменения применены."
	@echo "⚠️  РЕКОМЕНДАЦИЯ: Выполните 'source .bash_music' находясь в директории ~/Музыка."
	@echo "========================================================================"

venv:
	@echo "========================================================================"
	@if [ ! -d "$(VENV_DIR)" ]; then                                                           \
		echo "⚙️  Создание изолированного окружения RAG..."                               ; \
		sudo mkdir -p $(SHARE_DIR)                                                       ; \
		sudo chown $(WHOAMI):$(WHOAMI) -R /usr/share/$(PROJECT_NAME) 2>/dev/null || true ; \
		sudo chown $(WHOAMI):$(WHOAMI) -R $(SHARE_DIR)                                   ; \
		python3 -m venv $(VENV_DIR)                                                      ; \
		cp $(REQUIREMENTS_SRC) $(REQUIREMENTS_DST) || touch $(REQUIREMENTS_DST)          ; \
		if [ -f ".env" ]; then cp .env $(DOTENV_FN); else touch $(DOTENV_FN); fi         ; \
		$(VENV_DIR)/bin/pip3 install -r $(REQUIREMENTS_DST)                              ; \
		$(VENV_DIR)/bin/pip3 install torch --trusted-host download.pytorch.org --extra-index-url http://download.pytorch.org/whl/cpu ; \
	fi
	@echo "✅ Виртуальное окружение успешно создано и проверено."

git: git_local git_remote

git_local: 
	git add .
	git commit -a -m "Фиксация стабильного RAG-пайплайна"

git_remote: 
	git push origin rag-pipeline

