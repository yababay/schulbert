# =====================================================================
# МУЗЫКАЛЬНЫЙ АССИСТЕНТ «ШУЛЬБЕРТ» (ВЕРСИЯ ДЛЯ РАЗВОРАЧИВАНИЯ НА CUBI)
# =====================================================================

# Секция назначения путей на Cubi
PROJECT_NAME = schulbert
SHARE_DIR = /usr/share/$(PROJECT_NAME)
SYSTEMD_USER_DIR = $(HOME)/.config/systemd/user

.PHONY: all psql git git_local git_remote

# =====================================================================
# 1. ФАЗА ИНТЕНСИВНОЙ ОТЛАДКИ (Правка кода -> make setup)
# =====================================================================
all:
	@echo "⚙️  Обновление музыкального сервера…"
	cp command_checker.py $(SHARE_DIR)
	cp playlist_checker.py $(SHARE_DIR)
	cp track_checker.py $(SHARE_DIR)
	cp main.py $(SHARE_DIR)
	cp requirements.txt $(SHARE_DIR)
	mkdir -p $(SYSTEMD_USER_DIR)
	cp music-ai-search.service $(SYSTEMD_USER_DIR)/

	@echo "========================================================="
	@echo "✅ Скрипты и юнит обновлены, перезапускаем новую версию…"
	@echo "========================================================="

	systemctl --user daemon-reload
	systemctl --user restart $(MUSIC_AI_SEARCH_SERVICE)
	systemctl --user status  $(MUSIC_AI_SEARCH_SERVICE)

# =====================================================================
# 2. ВСПОМОГАТЕЛЬНЫЕ КОМАНДЫ
# =====================================================================
psql:
	psql -d player -U player -h localhost

git_local: 
	git add .
	git commit -a

git_remote: 
	git push origin music-ai-search

git: git_local git_remote


