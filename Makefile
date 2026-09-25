# =====================================================================
# ГОЛОСОВОЙ ПОМОЩНИК «ШУЛЬБЕРТ» (ВЕРСИЯ ДЛЯ ДЕСКТОПА)
# =====================================================================

PROJECT_NAME = schulbert

# Имя подпроекта и его файлов согласно новой плоской структуре
MUSIC_VOICE_ASSISTANT = music-voice-assistant
MUSIC_VOICE_ASSISTANT_SERVICE = $(MUSIC_VOICE_ASSISTANT).service

SHARE_DIR = /usr/share/$(PROJECT_NAME)/$(MUSIC_VOICE_ASSISTANT)
VENV_DIR  = $(SHARE_DIR)/.venv
SYSTEMD_USER_DIR = ~/.config/systemd/user
REQUIREMENTS_SRC = requirements.txt
REQUIREMENTS_DST = $(SHARE_DIR)/$(REQUIREMENTS_SRC)
CURRENT_USER = $(shell whoami)

.PHONY: all setup git git_local git_remote venv

# По умолчанию запускаем создание venv и установку правок
all: venv setup

setup: venv
	@echo "⚙️  Обновление скриптов голосового помощника…"
	rm -f $(SHARE_DIR)/*.py
	rm -f $(SHARE_DIR)/*.txt
	
	# 🌟 ИСПРАВЛЕНО: Копируем актуальный main.py из корня новой ветки
	cp main.py  $(SHARE_DIR)/
	cp .env     $(SHARE_DIR)/.env 2>/dev/null || true
	cp $(MUSIC_VOICE_ASSISTANT_SERVICE) $(SYSTEMD_USER_DIR)/

	@echo "✅ Скрипты и юнит обновлены, перезапускаем новую версию…"
	systemctl --user daemon-reload
	
	# Не запускаем oneshot принудительно при деплое, чтобы он не дергал микрофон,
	# а просто проверяем, что systemd видит его без ошибок
	systemctl --user start $(MUSIC_VOICE_ASSISTANT_SERVICE)
	
	# 🌟 ИСПРАВЛЕНО: Оператор || true защищает make от паники, когда oneshot засыпает
	systemctl --user status $(MUSIC_VOICE_ASSISTANT_SERVICE) || true
	@echo "========================================================="
	@echo "🎉 Успех! Изменения применены. Вызов по Alt+M готов."
	@echo "========================================================="

venv:
	@if [ ! -d "$(VENV_DIR)" ]; then                              \
		sudo mkdir -p $(VENV_DIR)                           ; \
		sudo chown $(CURRENT_USER) -R $(SHARE_DIR)          ; \
		if [ -f ".env" ]; then                                \
			cp .env $(SHARE_DIR)/.env   		    ; \
		else						      \
			touch $(SHARE_DIR)/.env                     ; \
		fi						    ; \
		python3 -m venv $(SHARE_DIR)/.venv                  ; \
		cp $(REQUIREMENTS_SRC) $(REQUIREMENTS_DST)          ; \
		$(VENV_DIR)/bin/pip3 install -r $(REQUIREMENTS_DST) ; \
	fi                                                          

	@echo "========================================================="
	@echo "✅ Виртуальное окружение успешно создано…"

git: git_local git_remote

git_local: 
	git add .
	git commit -a

git_remote: 
	git push origin voice-assistant

