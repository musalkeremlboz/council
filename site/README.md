# COUNCIL tanıtım sitesi

`site/build.py`, `brand/` tasarım sisteminden ve buradaki metin ve veri dosyalarından dört sayfalık iki dilli siteyi üretir. Yalnız Python'un kendi kitaplığını kullanır.

```sh
python site/build.py              # site/cikti/ altına yazar
python site/build.py --cikti DIR  # başka bir klasöre yazar
python site/build.py --gorsel     # paylaşım görsellerini Chrome ile yeniden çizer (yalnız metin ya da şablon değişince)
```

## Dosyalar

| Yol | İçerik |
|---|---|
| `build.py` | Üretici. Sayfaları doldurur, varlıkları kopyalar, glif alt kümesini yazar. |
| `sablon/sayfa.html` | Sayfa kabuğu (`string.Template`, `$` yer tutucuları): başlık, açıklama, dil eşleri, üst şerit, alt bilgi. |
| `sablon/ana.html` | Ana sayfanın gövdesi: açılış ve kurulum cümlesi, Çizgi ve söz, Ne işe yarar, Kurul turu, ürünler şeridi. Tekrarlanan parçalar (maddeler, paneller, ürünler) `build.py` içinde üretilir. |
| `sablon/paylas.svg` | Paylaşım görselinin şablonu (1200×630): koyu tema renkleri `brand/tokens.json`dan, amblem `brand/logo/`dan, slogan Council Halka ile (woff2 SVG'ye gömülür). Renk değeri yazılmaz. |
| `sablon/site.css` | Kabuğun yerleşimi. Yalnız `tokens.css` değişkenleri; renk değeri yazılmaz. |
| `sablon/site.js` | Açılış betiği: denetim kancası (`?denetim=1`), kimlik anı, kopyala düğmeleri (`data-kopyala`; sonuç yazıları sayfadan, `data-tamam` / `data-hata`) ve ana sayfadaki iki sahne. Betik yoksa kopyala düğmesi gizli kalır, cümle seçilebilir metindir. |
| `metin/tr.json`, `metin/en.json` | Bütün metinler (yalnız README.md ve README.en.md'den, kısaltılarak). İki dosyanın anahtarları birebir aynı olmalı; eksik ya da fazla anahtar derlemeyi durdurur. `{yolda}`, `{surum}`, `{temel}` gibi yer tutucular derlemede tek kaynaktan dolar. |
| `veri/urunler.json` | Ürünler şeridi (bugün yalnız Hafıza). Metinleri `metin` içinde `urunler.<anahtar>`. |
| `cikti/` | Üretilen site. Depoya girer; yayın buradan yapılır. Elle düzenlenmez. |

## Tek kaynaktan gelenler

- Renk, ölçü, bileşenler `brand/css/`; yazı tipleri `brand/font/`; logo `brand/logo/`; simgeler `brand/simge/`; sahneler `brand/js/sahne/`.
- Özellik adları ve durumları `brand/js/ozellikler.json`. Adı olan bir özelliğin `en` bloğu yoksa derleme durur.
- Kurul turu etiketlerindeki durum sözcüğü (`TAMAM`, `DENEMEDE`, `YOLDA`) özelliğin `ozellikler.json`daki durumundan, sözcüğün kendisi `brand/js/metin.json`dan; Çizgi ve söz biçimlerinin durağan SVG'leri `node brand/js/parca.mjs <dil>` ile üretilir (derleme için `node` gerekir).
- Araç sayıları `council/server.py` içindeki `@mcp.tool` işlevlerinden (`ast` ile okunur, sunucu içe aktarılmaz); sürüm `pyproject.toml`.

## Çıktı

- `cikti/index.html` (TR ana sayfa), `cikti/en/index.html`, `cikti/hafiza/index.html`, `cikti/en/memory/index.html`.
- `cikti/varlik/<özet>/`: kopyalanan varlıklar ve `glifler.json` (yalnız kimlik anında kurulan harfler). `<özet>`, kopyalanan her şeyin sha256 özetinin ilk 10 karakteridir; içerik değişince klasör adı da değişir, eski klasör silinir.
- `cikti/paylas-tr.png`, `cikti/paylas-en.png`: sayfaların `og:image` görselleri. Elle değil `--gorsel` ile üretilir ve depoya girer; `--gorsel`siz derleme bunları olduğu gibi kopyalar (Chrome gerekmez).
- `cikti/sitemap.xml` (dört adres, her birinde dil eşleri ve `x-default`) ve `cikti/robots.txt`.
- Derleme tekrarlanabilir: aynı girdi aynı baytları verir. `python site/build.py` sonrası `git status` temiz kalmalı; `tests/test_site_denetim.py` taze bir derlemeyi `cikti/` ile karşılaştırır.

## Denetim

`tests/test_site_build.py` ve `tests/test_site_denetim.py`: dört sayfa, dil eşleri, anahtar eşliği, araç sayıları, tekrarlanabilirlik, göreli varlık bağlantıları; araç adı ve kişisel sözcük taraması (`brand/icerik.py`), renk değeri yok, dış kaynak yok, dış bağlantılar yalnız GitHub, iç bağlantılar var olan dosyalara gider, sayfa başına sahne sınırı.

Tarayıcı denetimi (`tests/test_site_tarayici.py`, Chrome yoksa atlanır): dört sayfada 375 ve 1280 px'te yatay taşma yok; ana sayfalarda kimlik anı `kor-c-yazi-isaret` sırasıyla kurulur ve sonunda kaynak işaretleme geri gelir; azaltılmış harekette ve betiksiz `<main>` içinde yazı taşıyıp görünmeyen öğe yok (`?denetim=1` kancasının `data-gizli` değeri 0); site haritası ve robots.txt; paylaşım görselleri 1200×630. Ekran görüntüleri için: `python brand/denetle.py KLASOR --sayfa site/cikti/index.html --sayfa site/cikti/en/memory/index.html`.
