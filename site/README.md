# COUNCIL tanıtım sitesi

`site/build.py`, `brand/` tasarım sisteminden ve buradaki metin ve veri dosyalarından dört sayfalık iki dilli siteyi üretir: ana sayfa (Kurul Masası) ve Hafıza sayfası, her biri Türkçe ve İngilizce. Yalnız Python'un kendi kitaplığını kullanır.

```sh
python site/build.py              # site/cikti/ altına yazar
python site/build.py --cikti DIR  # başka bir klasöre yazar
python site/build.py --gorsel     # paylaşım görsellerini Chrome ile yeniden çizer (yalnız metin ya da şablon değişince)
```

## Dosyalar

| Yol | İçerik |
|---|---|
| `build.py` | Üretici. Sayfaları doldurur, varlıkları kopyalar, glif alt kümesini yazar. |
| `sablon/sayfa.html` | Sayfa kabuğu (`string.Template`, `$` yer tutucuları): başlık, açıklama, dil eşleri, `<main>`. Üst şeridi ve (Hafıza sayfalarında) alt bilgiyi `build.py` üretir; ana sayfa koyu açılır ve alt bilgisi yoktur (lisans son bölümde). |
| `sablon/ana.html` | Ana sayfanın gövdesi, Kurul Masası'nın beş bölümü: Açılış (slogan, kurulum cümlesi), Canlı, Nasıl çalışır, Yol haritası, Yardımcılar. Tekrarlanan satırlar `build.py` içinde üretilir. Tuval, ızgara ve koltuk sırası `ana_once()` ile `<main>`in önüne konur. |
| `sablon/masa.css`, `sablon/masa.js` | Kurul Masası'nın biçemi ve betiği; yalnız ana sayfada yüklenir (`masa.js`'i `site.js` tuval varsa içe aktarır). Tek tuval parçacık alanıdır; altta beş koltuk (`tablist`) bölümleri açar. Betik her metni sayfadan okur; kurulumu bitince kökü `masa-js` ile işaretler (markanın erken konan `js` sınıfı değil), gizleyen her kural bunun altındadır, betik yüklenmezse bölümler alt alta okunur; renkleri `getComputedStyle` ile token'lardan alır. |
| `sablon/paylas.svg` | Paylaşım görselinin şablonu (1200×630): koyu tema renkleri `brand/tokens.json`dan, amblem `brand/logo/`dan, slogan Council Halka ile (woff2 SVG'ye gömülür). Renk değeri yazılmaz. |
| `sablon/site.css` | Kabuğun yerleşimi. Yalnız `tokens.css` değişkenleri; renk değeri yazılmaz. |
| `sablon/site.js` | Açılış betiği: denetim kancası (`?denetim=1`), kimlik anı (üst şeritteki yazıyı kurar), kopyala düğmeleri (`data-kopyala`; sonuç yazıları sayfadan, `data-tamam` / `data-hata`) ve ana sayfada `masa.js`. Betik yoksa kopyala düğmesi gizli kalır, cümle seçilebilir metindir. |
| `metin/tr.json`, `metin/en.json` | Bütün metinler (yalnız README.md ve README.en.md'den, kısaltılarak). İki dosyanın anahtarları birebir aynı olmalı; eksik ya da fazla anahtar derlemeyi durdurur. `{yolda}`, `{surum}`, `{temel}` gibi yer tutucular derlemede tek kaynaktan dolar. |
| `veri/urunler.json` | Üst şeridin solundaki ürünler (bugün yalnız Hafıza). Adları `metin` içinde `urunler.<anahtar>.ad`. |
| `veri/yardimcilar.json` | Desteklenen yardımcı satırları (ad, destek metni, durum); hem ana sayfanın son bölümünde hem Hafıza sayfasında. Araç adları yalnız bu dosyadan gelen bloklarda geçer. |
| `cikti/` | Üretilen site. Depoya girer; yayın buradan yapılır. Elle düzenlenmez. |

## Tek kaynaktan gelenler

- Renk, ölçü, bileşenler `brand/css/`; yazı tipleri `brand/font/`; logo `brand/logo/`; simgeler `brand/simge/`; sahneler `brand/js/sahne/`.
- Özellik adları ve durumları `brand/js/ozellikler.json`. Adı olan bir özelliğin `en` bloğu yoksa derleme durur. Yol haritası satırları buradan kurulur (adlı özellik kendi satırı, art arda adsızlar tek satır: "3–6"); halkanın altı parçasının durumu `data-durumlar` ile betiğe gider. Rozetteki durum sözcüğü `brand/js/metin.json`dan.
- Yardımcı satırları `veri/yardimcilar.json`; kurulum cümlesi `ana.kurulum.cumle`; komutlar `build.py` içinde `KUR_UNIX`, `KUR_WINDOWS`.
- Canlı bölümün konuşması metin dosyasında (`ana.canli.satirlar`); sayfada yazılı gelir (betiksiz okunur), `masa.js` onu okuyup yeniden oynatır.
- Araç sayıları `council/server.py` içindeki `@mcp.tool` işlevlerinden (`ast` ile okunur, sunucu içe aktarılmaz); sürüm `pyproject.toml`.

## Çıktı

- `cikti/index.html` (TR ana sayfa, Kurul Masası), `cikti/en/index.html`, `cikti/hafiza/index.html`, `cikti/en/memory/index.html`.
- `cikti/varlik/<özet>/`: kopyalanan varlıklar ve `glifler.json` (yalnız kimlik anında kurulan harfler). `<özet>`, kopyalanan her şeyin sha256 özetinin ilk 10 karakteridir; içerik değişince klasör adı da değişir, eski klasör silinir.
- `cikti/paylas-tr.png`, `cikti/paylas-en.png`: sayfaların `og:image` görselleri. Elle değil `--gorsel` ile üretilir ve depoya girer; `--gorsel`siz derleme bunları olduğu gibi kopyalar (Chrome gerekmez).
- `cikti/sitemap.xml` (dört adres, her birinde dil eşleri ve `x-default`) ve `cikti/robots.txt`.
- Derleme tekrarlanabilir: aynı girdi aynı baytları verir. `python site/build.py` sonrası `git status` temiz kalmalı; `tests/test_site_denetim.py` taze bir derlemeyi `cikti/` ile karşılaştırır.

## Denetim

`tests/test_site_build.py` ve `tests/test_site_denetim.py`: dört sayfa, dil eşleri, anahtar eşliği, araç sayıları, tekrarlanabilirlik, göreli varlık bağlantıları; ana sayfada beş bölüm kimliği ve sırası, slogan, kurulum cümlesi ve tek `c-dugme--kor`, yol haritası ve yardımcı satırlarının kaynaklardan gelmesi, "Bugün" satırı, üst şerit düzeni, EN sayfalarda Türkçe harf yok, ağırlık bütçesi; araç adı ve kişisel sözcük taraması (`brand/icerik.py`), renk değeri yok, dış kaynak yok, dış bağlantılar yalnız GitHub, iç bağlantılar var olan dosyalara gider, sahne sınırı (ana sayfada tek tuval, Hafıza'da yok).

Tarayıcı denetimi (`tests/test_site_tarayici.py`, Chrome yoksa atlanır): dört sayfada 375 ve 1280 px'te yatay taşma yok; kimlik anı üst şeritteki yazıyı (`yazi`) kurar ve sonunda kaynak işaretleme geri gelir; ana sayfada yedi pencere boyutunda (375×812, 812×375, 820×1180, 1180×820, 950×1150, 1280×800, 1920×1080) bölümlerde ve sayfada yatay taşma yok, her koltuk kendi bölümünü açar ve başka bölüm açık kalmaz, klavye (koltuklarda ok, Home, End; 1–5, PageUp, PageDown) çalışır; kapalı bölümler `hidden` olduğundan görünmeyen yazı sayılmaz; azaltılmış harekette ve betiksiz `<main>` içinde yazı taşıyıp görünmeyen öğe yok (`?denetim=1` kancasının `data-gizli` değeri 0); site haritası ve robots.txt; paylaşım görselleri 1200×630. Ekran görüntüleri için: `python brand/denetle.py KLASOR --sayfa site/cikti/index.html --sayfa site/cikti/en/memory/index.html`.

## Yayın

Yayın, `site/` temizken (commitli) yapılır. İlk yayından önce aşağıdaki Caddy bloğu eklenmiş olmalı.

```sh
python site/build.py
site/yayinla.sh kullanici@sunucu:/var/www/council-site   # ya da yerel bir klasör
site/dogrula.sh https://council.systems
```

- `yayinla.sh <hedef>`: önce `site/cikti/` klasörünün taze bir `build.py` çıktısıyla aynı olduğunu denetler (farklıysa durur). Sonra `site/cikti/` klasörünü `<hedef>/surumler/<git kısa özeti>/` altına `rsync -a --delete` ile kopyalar, `<hedef>/guncel` bağını yeni sürüme çevirir (uzakta `ln -sfn` ve `mv -T` ile tek adımda; yerelde `ln -sfn`); yayından önce o an canlı sürümün `varlik/<özet>/` klasörlerinden yeni sürümde olmayanlar yeni sürüme taşınır (`rsync --ignore-existing`), böylece geçiş sırasında açık olan sayfaların istediği varlıklar 404 olmaz, `surumler/` içinde en yeni 3 klasörü tutar. `site/` kirliyse durur. `SURUM=ad` sürüm adını değiştirir (testler için).
- `dogrula.sh <temel-adres>`: `/`, `/en/`, `/hafiza/`, `/en/memory/`, `/sitemap.xml` için 200; değişmeyen hizmet yolları için `/health`, `/icon.svg`, `/.well-known/oauth-authorization-server` 200, `/mcp`, `/panel/` ve `/login` 404 değil. `/` yanıtında yeni sitenin canonical bağı aranır (eski sunucu da 200 verir). Her denetim bir satır; biri başarısızsa çıkış kodu sıfırdan farklıdır. `DOGRULA_SAYFALAR_YALNIZ=1` hizmet yollarını atlar (yerel dosya sunucusu).

### Uzak hedef

- Hedefte kullanıcı adı yazılmalı (`kullanici@sunucu:/yol`): `yayinla.sh` uzak hedefi `@` ile tanır; `@` yoksa hedefi yerel klasör sanar.
- Sunucuda `rsync` ve GNU `mv -T` gerekir. Caddy'nin kullanıcısı dosyaları okuyabilmeli; `site/cikti/` dosyaları herkese okunur.

### Caddy bloğu

Canlı `council.systems` bloğunda, hizmete giden diğer `handle` kurallarının yanında ve her şeyi yakalayan `reverse_proxy` satırından önce (sırayı görmek için `caddy adapt`):

```caddy
@varlik path /varlik/*
@site path / /en /en/* /hafiza /hafiza/* /sitemap.xml /robots.txt /paylas-tr.png /paylas-en.png
handle @varlik {
	root * /var/www/council-site/guncel
	header Cache-Control "public, max-age=31536000, immutable"
	file_server
}
handle @site {
	root * /var/www/council-site/guncel
	header Cache-Control "no-cache"
	file_server
}
```

`/varlik/*` yolları içerik özetli olduğu için sonsuza dek önbelleğe alınır; HTML ve diğer dosyalar `no-cache`. Yayından önce `caddy validate` ve `curl -I` ile iki yolun başlığına bakılmalı.

### Geri alma

- Bir sürüm geri: `guncel` bağını bir önceki `surumler/<ad>` klasörüne çevir (`ln -sfn surumler/<ad> guncel`).
- Bütünüyle: bloğu sil, `caddy validate`, `systemctl reload caddy`.
