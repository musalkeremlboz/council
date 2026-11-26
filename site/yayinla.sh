#!/bin/sh
# Publish site/cikti/ as a new version folder and switch <hedef>/guncel to it.
# Usage: site/yayinla.sh <hedef>   (user@host:/var/www/council-site, or a local directory)
# Env:   SURUM=<ad> overrides the version name (tests); default is the short git HEAD.
set -eu

hedef=${1:-}
[ -n "$hedef" ] || { echo "kullanim: site/yayinla.sh <hedef>" >&2; exit 2; }

kok=$(cd "$(dirname "$0")/.." && pwd)
cd "$kok"

if [ -n "$(git status --porcelain site/)" ]; then
  echo "site/ icinde commitlenmemis degisiklik var; once commitle." >&2
  exit 1
fi
[ -d site/cikti ] || { echo "site/cikti/ yok; once python site/build.py" >&2; exit 1; }

surum=${SURUM:-$(git rev-parse --short HEAD)}
case "$surum" in
  ''|*[!A-Za-z0-9._-]*) echo "gecersiz surum adi: $surum" >&2; exit 1 ;;
esac

case "$hedef" in
  *@*:*)
    host=${hedef%%:*}
    yol=${hedef#*:}
    ssh "$host" "mkdir -p '$yol/surumler/$surum'"
    rsync -a --delete site/cikti/ "$host:$yol/surumler/$surum/"
    # Linux remote: atomic switch (mv -T), keep the newest 3 versions by mtime.
    ssh "$host" 'sh -s' <<REMOTE
set -eu
cd '$yol'
touch 'surumler/$surum'
ln -s 'surumler/$surum' guncel.yeni
mv -T guncel.yeni guncel
cd surumler
ls -1t | tail -n +4 | while read -r eski; do rm -rf -- "\$eski"; done
REMOTE
    ;;
  *)
    mkdir -p "$hedef/surumler/$surum"
    rsync -a --delete site/cikti/ "$hedef/surumler/$surum/"
    # rsync -a copies the source dir's mtime onto the folder; make it "now" so pruning is by publish order.
    touch "$hedef/surumler/$surum"
    (cd "$hedef" && ln -sfn "surumler/$surum" guncel)
    (cd "$hedef/surumler" && ls -1t | tail -n +4 | while read -r eski; do rm -rf -- "$eski"; done)
    ;;
esac

echo "yayinlandi: $surum -> $hedef"
