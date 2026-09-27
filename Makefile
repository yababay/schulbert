# =====================================================================
# АССИСТЕНТ «ШУЛЬБЕРТ»: РАБОТА С ПЛЕЙЛИСТАМИ
# =====================================================================

.PHONY: all git_local git_remote

all: git_local git_remote

git_local: 
	git add .
	git commit -a

git_remote: 
	git push origin playlists

