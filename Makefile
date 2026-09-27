# =====================================================================
# АССИСТЕНТ «ШУЛЬБЕРТ»: РАБОТА С ПЛЕЙЛИСТАМИ
# =====================================================================

DB_DUMP_FN = music-ai-search.sql

.PHONY: all dump git_local git_remote

all: git_local git_remote

git_local: 
	git add .
	git commit -a

git_remote: 
	git push origin playlists

dump:
	pg_dump -h schulbert -U player -F p --clean -b -f $(DB_DUMP_FN) player
	yc storage s3 mv $(DB_DUMP_FN) s3://playlists-dispatcher/playlists/

