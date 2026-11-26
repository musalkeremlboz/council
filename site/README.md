# COUNCIL tanıtım sitesi

`site/build.py`, `brand/` tasarım sisteminden ve buradaki metin ve veri dosyalarından dört sayfalık iki dilli siteyi üretir. Yalnız Python'un kendi kitaplığını kullanır.

```sh
python site/build.py              # site/cikti/ altına yazar
python site/build.py --cikti DIR  # başka bir klasöre yazar
```

## Dosyalar

| Yol | İçerik |
|---|---|
| `build.py` | Üretici. Sayfaları doldurur, varlıkları kopyalar, glif alt kümesini yazar. |
| `sablon/sayfa.html` | Sayfa kabuğu (`string.Template`, `$` yer tutucuları): başlık, açıklama, dil eşleri, üst şerit, alt bilgi. |
| `sablon/site.css` | Kabuğun yerleşimi. Yalnız `tokens.css` değişkenleri; renk değeri yazılmaz. |
| `sablon/site.js` | Açılış betiği: denetim kancası (`?denetim=1`) ve kimlik anı. |
| `metin/tr.json`, `metin/en.json` | Bütün metinler. İki dosyanın anahtarları birebir aynı olmalı; eksik ya da fazla anahtar derlemeyi durdurur. |
| `veri/urunler.json` | Ürünler şeridi (bugün yalnız Hafıza). Metinleri `metin` içinde `urunler.<anahtar>`. |
| `cikti/` | Üretilen site. Depoya girer; yayın buradan yapılır. Elle düzenlenmez. |

## Tek kaynaktan gelenler

- Renk, ölçü, bileşenler `brand/css/`; yazı tipleri `brand/font/`; logo `brand/logo/`; simgeler `brand/simge/`; sahneler `brand/js/sahne/`.
- Özellik adları ve durumları `brand/js/ozellikler.json`. Adı olan bir özelliğin `en` bloğu yoksa derleme durur.
- Araç sayıları `council/server.py` içindeki `@mcp.tool` işlevlerinden (`ast` ile okunur, sunucu içe aktarılmaz); sürüm `pyproject.toml`.

## Çıktı

- `cikti/index.html` (TR ana sayfa), `cikti/en/index.html`, `cikti/hafiza/index.html`, `cikti/en/memory/index.html`.
- `cikti/varlik/<özet>/`: kopyalanan varlıklar ve `glifler.json` (yalnız kimlik anında kurulan harfler). `<özet>`, kopyalanan her şeyin sha256 özetinin ilk 10 karakteridir; içerik değişince klasör adı da değişir, eski klasör silinir.
- Derleme tekrarlanabilir: aynı girdi aynı baytları verir. `python site/build.py` sonrası `git status` temiz kalmalı; `tests/test_site_denetim.py` taze bir derlemeyi `cikti/` ile karşılaştırır.

## Denetim

`tests/test_site_build.py` ve `tests/test_site_denetim.py`: dört sayfa, dil eşleri, anahtar eşliği, araç sayıları, tekrarlanabilirlik, göreli varlık bağlantıları; araç adı ve kişisel sözcük taraması (`brand/icerik.py`), renk değeri yok, dış kaynak yok, dış bağlantılar yalnız GitHub, iç bağlantılar var olan dosyalara gider, sayfa başına sahne sınırı.
