#!/bin/sh
# Check a live (or local) base URL: new pages 200, service routes unchanged.
# Usage: site/dogrula.sh <base-url>
# Env:   DOGRULA_SAYFALAR_YALNIZ=1 skips the service-route checks (local file server).
set -u

taban=${1:-}
[ -n "$taban" ] || { echo "kullanim: site/dogrula.sh <base-url>" >&2; exit 2; }
taban=${taban%/}
hata=0

kod() { curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$taban$1" || true; }

# bekle: 200 | yok404 (anything but 404 and 000)
kontrol() {
  yol=$1; beklenen=$2
  sonuc=$(kod "$yol")
  case "$beklenen" in
    200) [ "$sonuc" = 200 ] && ok=1 || ok=0 ;;
    *)   [ "$sonuc" != 404 ] && [ "$sonuc" != 000 ] && ok=1 || ok=0 ;;
  esac
  if [ "$ok" = 1 ]; then echo "OK   $sonuc $yol"; else echo "FAIL $sonuc $yol (beklenen: $beklenen)"; hata=1; fi
}

for y in / /en/ /hafiza/ /en/memory/ /sitemap.xml; do kontrol "$y" 200; done

if [ "${DOGRULA_SAYFALAR_YALNIZ:-}" != 1 ]; then
  for y in /health /icon.svg /.well-known/oauth-authorization-server; do kontrol "$y" 200; done
  for y in /mcp /panel/; do kontrol "$y" yok404; done
fi

exit "$hata"
