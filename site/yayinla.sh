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

# site/cikti/ must be what the generator produces from the committed sources right now.
if [ -f site/build.py ]; then
  if [ -n "${PYTHON:-}" ]; then py=$PYTHON; elif [ -x .venv/bin/python ]; then py=.venv/bin/python; else py=python3; fi
  taze=$(mktemp -d)
  trap 'rm -rf "$taze"' EXIT
  "$py" site/build.py --cikti "$taze" >/dev/null || { echo "site/build.py calismadi." >&2; exit 1; }
  if ! diff -r site/cikti "$taze" >/dev/null 2>&1; then
    echo "site/cikti/ eski: site/build.py ciktisindan farkli. python site/build.py calistirip sonucu commitle." >&2
    exit 1
  fi
fi

surum=${SURUM:-$(git rev-parse --short HEAD)}
case "$surum" in
  ''|*[!A-Za-z0-9._-]*) echo "gecersiz surum adi: $surum" >&2; exit 1 ;;
esac

case "$hedef" in
  *@*:*)
    host=${hedef%%:*}
    yol=${hedef#*:}
    ssh "$host" "mkdir -p '$yol/surumler/$surum'"
    # protect varlik/*: a re-publish of the same name must not drop hashes carried over from earlier releases.
    rsync -a --delete --filter='protect /varlik/*' site/cikti/ "$host:$yol/surumler/$surum/"
    # Linux remote: atomic switch (mv -T), keep the newest 3 versions by mtime.
    ssh "$host" 'sh -s' <<REMOTE
set -eu
cd '$yol'
touch 'surumler/$surum'
# Carry the live release's hashed asset folders forward: pages already open still fetch them after the switch.
if [ -d guncel/varlik ]; then
  mkdir -p 'surumler/$surum/varlik'
  rsync -a --ignore-existing guncel/varlik/ 'surumler/$surum/varlik/'
fi
ln -sfn 'surumler/$surum' guncel.yeni
mv -T guncel.yeni guncel
cd surumler
ls -1t | tail -n +4 | while read -r eski; do rm -rf -- "\$eski"; done
REMOTE
    ;;
  *)
    mkdir -p "$hedef/surumler/$surum"
    rsync -a --delete --filter='protect /varlik/*' site/cikti/ "$hedef/surumler/$surum/"
    # Carry the live release's hashed asset folders forward: pages already open still fetch them after the switch.
    if [ -d "$hedef/guncel/varlik" ]; then
      mkdir -p "$hedef/surumler/$surum/varlik"
      rsync -a --ignore-existing "$hedef/guncel/varlik/" "$hedef/surumler/$surum/varlik/"
    fi
    # rsync -a copies the source dir's mtime onto the folder; make it "now" so pruning is by publish order.
    touch "$hedef/surumler/$surum"
    (cd "$hedef" && ln -sfn "surumler/$surum" guncel)
    (cd "$hedef/surumler" && ls -1t | tail -n +4 | while read -r eski; do rm -rf -- "$eski"; done)
    ;;
esac

echo "yayinlandi: $surum -> $hedef"
