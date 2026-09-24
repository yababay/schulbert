# =====================================================================
# МУЗЫКАЛЬНЫЙ АССИСТЕНТ «ШУЛЬБЕРТ» (ВЕРСИЯ ДЛЯ NATIVE-СБОРКИ НА CUBI)
# =====================================================================

PROJECT_NAME = schulbert
PROJECT_DIR  = $(shell pwd)
HOME_DIR     = $(HOME)
BUILD_DIR    = build/$(PROJECT_NAME)
MUSIC_DIR    = $(HOME_DIR)/Music

# Файлы проекта согласно вашей плоской структуре
MUSIC_AI_SEARCH       = music-ai-search
THD_BLUETOOTH_MONITOR = thd-bluetooth-monitor
MUSIC_AI_SEARCH_SCRIPT  = $(MUSIC_AI_SEARCH).py
MUSIC_AI_SEARCH_SERVICE = $(MUSIC_AI_SEARCH).service
THD_BLUETOOTH_MONITOR_SCRIPT  = $(THD_BLUETOOTH_MONITOR).sh
THD_BLUETOOTH_MONITOR_SERVICE = $(THD_BLUETOOTH_MONITOR).service

# Секция назначения путей на Cubi
SHARE_DIR = /usr/share/$(PROJECT_NAME)
SYSTEMD_USER_DIR   = $(HOME_DIR)/.config/systemd/user
SYSTEMD_SYSTEM_DIR = /etc/systemd/system

.PHONY: all setup clean prepare build git_commit psql db_backup db_restore git git_local git_remote

# По умолчанию (просто 'make') — собираем готовый дебиан-пакет
all: prepare build

# =====================================================================
# 1. ФАЗА ИНТЕНСИВНОЙ ОТЛАДКИ (Правка кода -> make setup)
# =====================================================================
setup:
	@echo "⚙️  [Локальный деплой]: Обновление скриптов и юнитов Systemd…"
	sudo mkdir -p $(SHARE_DIR)
	sudo mkdir -p $(SHARE_DIR)
	sudo chown player -R $(SHARE_DIR)
	rm $(SHARE_DIR)/*.sh
	rm $(SHARE_DIR)/*.py
	rm $(SHARE_DIR)/*.txt
	mkdir -p $(SYSTEMD_USER)
	
	cp $(MUSIC_AI_SEARCH_SCRIPT)        $(SHARE_DIR)/
	cp $(MUSIC_AI_SEARCH_SERVICE)       $(SYSTEMD_USER_DIR)/
	cp $(THD_BLUETOOTH_MONITOR_SCRIPT)  $(SHARE_DIR)/
	chmod +x $(SHARE_DIR)/$(THD_BLUETOOTH_MONITOR_SCRIPT)
	sudo cp $(THD_BLUETOOTH_MONITOR_SERVICE) $(SYSTEMD_SYSTEM_DIR)/
	cp requirements.txt $(SHARE_DIR)/
	@echo "========================================================="
	@echo "✅ Скрипты и юниты обновлены, перезапускаем новые версии…"
	@echo "========================================================="

	systemctl --user daemon-reload
	systemctl --user restart $(MUSIC_AI_SEARCH_SERVICE)
	sudo systemctl daemon-reload
	sudo systemctl restart $(THD_BLUETOOTH_MONITOR_SERVICE)
	systemctl --user status $(MUSIC_AI_SEARCH_SERVICE)
	sudo systemctl status $(THD_BLUETOOTH_MONITOR_SERVICE)

# =====================================================================
# 2. ФАЗА СТАБИЛЬНОГО РЕЛИЗА (Сборка монолитного пакета)
# =====================================================================
clean:
	rm -rf $(BUILD_DIR)
	rm -f $(HOME_DIR)/deb_build/$(PROJECT_NAME).deb

prepare: clean db_backup
	@echo "📦 [Сборка пакета]: Формирование файлового дерева пакета..."
	mkdir -p $(BUILD_DIR)/DEBIAN
	mkdir -p $(BUILD_DIR)$(SHARE_DIR)
	mkdir -p $(BUILD_DIR)/etc/systemd/user
	mkdir -p $(BUILD_DIR)/etc/systemd/system
	mkdir -p $(BUILD_DIR)/var/lib/mpd/playlists
	mkdir -p $(BUILD_DIR)/usr/local/bin
	
	# Копируем метаданные Debian (контроль и постинсталл) из корня проекта
	cp $(PROJECT_DIR)/control $(BUILD_DIR)/DEBIAN/
	cp $(PROJECT_DIR)/postinst $(BUILD_DIR)/DEBIAN/
	chmod +x $(BUILD_DIR)/DEBIAN/postinst
	
	# Копируем скрипты и зависимости в пакет
	cp $(PROJECT_DIR)/$(SERVER_SCRIPT) $(BUILD_DIR)$(SHARE_DIR)/
	cp $(PROJECT_DIR)/query_normalizer.py $(BUILD_DIR)$(SHARE_DIR)/
	cp $(PROJECT_DIR)/requirements.txt $(BUILD_DIR)$(SHARE_DIR)/
	
	# Копируем глобальные бинарники
	cp $(PROJECT_DIR)/yaml2rag.py $(BUILD_DIR)/usr/local/bin/yaml2rag
	cp $(PROJECT_DIR)/$(TH_MONITOR) $(BUILD_DIR)/usr/local/bin/$(TH_MONITOR)
	
	# Копируем плейлисты для автодеплоя
	cp $(MUSIC_DIR)/*.m3u $(BUILD_DIR)/var/lib/mpd/playlists/ 2>/dev/null || true
	
	# Распределяем systemd юниты по уровням (пользовательский и системный для thd)
	cp $(PROJECT_DIR)/music-ai-search.service $(BUILD_DIR)/etc/systemd/user/
	if [ -f "$(PROJECT_DIR)/bluetooth-thd-restart.service" ]; then \
		cp $(PROJECT_DIR)/bluetooth-thd-restart.service $(BUILD_DIR)/etc/systemd/system/; \
	fi

build:
	dpkg-deb --build $(BUILD_DIR)
	mv $(HOME_DIR)/deb_build/$(PROJECT_NAME).deb $(PROJECT_DIR)/
	@echo "========================================================="
	@echo "🎉 Успех! Стабильный пакет $(PROJECT_NAME).deb собран."
	@echo "========================================================="

# =====================================================================
# 3. ВСПОМОГАТЕЛЬНЫЕ КОМАНДЫ СУБД И GIT
# =====================================================================
psql:
	psql -d player -U player

db_backup:
	pg_dump -h localhost -U player -F p --clean -b -f "$(MUSIC_DIR)/player_semantic_db.sql" player

db_restore:
	sed 's/OWNER TO mabel/OWNER TO player/g; s/TO mabel/TO player/g; /CREATE EXTENSION IF NOT EXISTS vector/d' $(MUSIC_DIR)/player_semantic_db.sql | psql -h localhost -U player -d player

git_local: 
	git add .
	git commit -a

git_remote: 
	git push origin main

git: git_local git_remote

