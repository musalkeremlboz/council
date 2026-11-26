# COUNCIL marka kitabı 0.2

Bu klasör tasarım sisteminin tek kaynağıdır. Panel, site ve ileride Kasa aynı dosyaları kullanır. Hiçbir değer iki yerde tutulmaz. Renk, yazı, boşluk, köşe ve hareket kuralları değerin adını yanında taşır. Bileşen ölçüleri (Tek Kesik boyları, düğme yazı boyu, 2 piksel odak çizgisi, 6 piksel şerit ve işaret) token değildir; spec sabitidir, rakamıyla yazılır ve `brand/css/council.css` içinde durur.

## Temel fikir

Logonun her parçası tek kuraldan çıkar: tam bir halka alınır ve düz bir kesimle kesilir.

> Halka durumu söyler, kesik eylemi söyler.

- Tıklanan her öğenin sağ üstünde tek bir 45° kesik vardır. Tıklanmayan hiçbir şeyde kesik olmaz.
- Bekleyen, çalışan, biten ve hafızaya yazılan durumlar halkayla gösterilir.
- Köşe üç değerden biridir: `kose-0`, `kose-tam` ya da 45° kesik. Gölge ve renk geçişi yoktur.

## Renk

Bütün renkler `tokens.json` içinde, iki temalıdır (açık, koyu). Başka yerde renk kodu yazılmaz.

- Yüzeyler: `zemin` sayfa için, `yuzey` kart ve alan için, `yuzey-2` seçili sekme ve girintili blok için.
- Metin: `murekkep` ana metin, `murekkep-2` ikincil, `murekkep-3` ipucu ve alt bilgi.
- Çizgi: `cizgi` ince ayırıcı, `cizgi-guclu` alan çerçevesi ve işaret kutusu.
- Kor: `kor` ekranda tek bir şeydir: hafıza, en önemli eylem ya da odaktaki öğe. İkinci bir kor öğe konmaz.
- Kor üstündeki yazı her zaman `kor-ustu` olur, beyaz olmaz.
- Kor renkli metin ve odak çizgisi `kor-metin` ile yazılır. Hafif kor zemin için `kor-zemin`.
- Durum: `basari`, `uyari`, `hata`. Her zaman bir sözcükle birlikte kullanılır. `hata` kor ile karışmasın diye pembeye çekiktir.
- Düğme halleri: basılan birincil düğme `murekkep-bas`, basılan kor düğme `kor-bas`, devre dışı düğme `pasif-zemin` ve `pasif-yazi`, hafif dolgu `ton`.
- Karşıtlık: metin her temada en az 4.5:1. 24 piksel ve üstü yazı, kontrol kenarı ve odak çizgisi 3:1. `python brand/build.py` sınırın altındaki çifti reddeder.

## Yazı

- `font-display` (Council Halka): başlık, logo, ürün adı. 24 pikselin altında kullanılmaz, paragraf dizilmez.
- `font-sans` (DM Sans): okuma metni ve arayüz.
- `font-mono` (DM Mono): kod, komut, yol, kayıt satırı.
- Başlıklar: `baslik-xl` kapakta bir kez, `baslik-l` sayfa başlığı, `baslik-m` bölüm başlığı.
- Metin: `govde-l` giriş, `govde` varsayılan, `govde-k` yardımcı metin ve tablo, `etiket` küçük büyük harfli etiket, `kod` komut ve yol.
- Yazı tipleri yerel dosyadan yüklenir (`brand/font/`). Dış sunucuya istek atılmaz.
- Council Halka 0.2 küçük harfleri de içerir. Büyük harfler ve rakamlar değişmez, logo SVG'leri birebir aynı çıkar.

## Boşluk

Ölçek sabittir, ara değer uydurulmaz.

- `ara-1` simge ile yazısı arası.
- `ara-2` bağlı öğeler arası.
- `ara-3` alan içi dolgu.
- `ara-4` küçük kart dolgusu ve telefon kenar boşluğu.
- `ara-6` kart içi dolgu ve grup araları.
- `ara-8` bölüm içi bloklar.
- `ara-12` bölümler arası.
- `ara-16` sayfa açılışı ve büyük boşluklar.

## Köşe

- `kose-0`: kart, alan, düğme gövdesi.
- `kose-tam`: halka, radyo düğmesi, rozetin yuvarlak yanı.
- 45° kesik: tıklanan öğenin sağ üstü. Ölçüsü yükseklikten hesaplanır.
- Başka köşe yoktur.

## Tek Kesik

Kesik ölçüsü `k = yükseklik × 2/7`.

| Boy | Yükseklik | Kesik | Yazı | Not |
|---|---|---|---|---|
| Orta | 44 px | 12 px | 15 px | Varsayılan |
| Küçük | 32 px | 9 px | 14 px | Yalnız fareli cihaz. Dokunmatikte 44/12 olur |
| Büyük | 56 px | 16 px | 17 px | Sitede |

- Dokunma hedefi en az 44 piksel.
- Üzerine gelince (yalnız fare) kesik 4 piksel açılır, `sure-tepki`. Basınca 4 piksel kapanır, `sure-bas`, gövde `murekkep-bas` ya da `kor-bas` olur.
- Odak: 2 piksel `kor-metin` çizgi, sağ üstü açık bir C gibi düğmeyi sarar. Her zaman görünür.
- Devre dışı: kesik kapanır, düz kare olur, `pasif-zemin` ve `pasif-yazi` kullanılır.
- Yükleniyor: `aria-busy="true"`, yanda dönen C. 300 ms'den kısa işte gösterilmez.
- Yüksek karşıtlık (`forced-colors`): kesik gider, yerine düz çerçeve gelir.

## Bileşenlerin dilbilgisi

Kural tektir: tıklanıyorsa kesik vardır, tıklanmıyorsa yoktur.

| Bileşen | Sınıf | Biçim |
|---|---|---|
| Düğme | `c-dugme` | Kor, birincil, ikincil, hayalet. Kesikli. Kor türü ekranda en fazla bir tane |
| Alan | `c-alan` | Köşe `kose-0`, kesik yok, 44 px, çerçeve `cizgi-guclu`. Etiketi her zaman görünür |
| Kart | `c-kart` | Düz kare. Tıklanan kartta (`c-kart--tik`) sabit kesik, içine ikinci düğme konmaz |
| Rozet | `c-rozet` | Durum bildirir, kesik yok. İçinde işaret, yanında sözcük |
| Durum işareti | `c-durum` | Açık C hazır, dönen C çalışıyor, tam O tamam, kor O hafızaya yazıldı, yarım halka hata |
| İlerleme | `c-halka`, `c-serit` | Dairesel olanın uçları düz. Doğrusal şerit 6 px, ilerleyen ucu kesik |
| Gezinme | `c-gezinme` | Düz metin. Bulunulan sayfanın solunda 6 px dolu daire |
| Sekme | `c-sekmeler` | Seçili sekme sağ üstü kesik `yuzey-2` bloğu |
| Menü | `c-menu` | Sağ üstten 45° çizgiyle açılır, `sure-panel` |
| İşaret kutusu, radyo | `c-isaret`, `c-radyo` | İşaret kutusu kare, radyo halka |
| Metin içi bağlantı | `c-baglanti` | Kesik yok, `murekkep` renkli alt çizgi |

## Hareket

Üç katman vardır. Bir ekranda aynı anda yalnız biri kendiliğinden hareket eder.

1. **Arayüz hareketi.** Her sayfada, sakin. Süreler: `sure-bas` 70 ms, `sure-tepki` 140 ms, `sure-panel` 240 ms, `sure-sahne` 420 ms.
2. **Kimlik anı.** Oturumda bir kez, açılışta. En fazla 1,8 sn, ilk ekrandaki metin 1,2 sn içinde okunur.
3. **Sahne.** Anlatı için. Sayfada en fazla iki yerde.

Kurallar:

- Eğriler: açılış ve geliş `egri-ac`, kapanış ve gidiş `egri-kapa`, dönen her şey doğrusal.
- Sahne geçişi en çok `sure-gecis-en-cok` (840 ms).
- Yalnız halka, kesik ve dalga hareket eder. Ölçek, zıplama, gölge, parlama yoktur.
- Sonsuz döngü yoktur. Sayfa boştayken sıfır kare çizilir. Ekran dışındaki sahne durur.
- Kaydırmalı sahne en fazla 450vh sürer ve bir "atla" bağlantısı taşır. Sahne dosyası 15 KB'ı geçmez.
- `prefers-reduced-motion` açıksa her sahnenin durağan, eksiksiz bir karşılığı vardır.
- JavaScript yoksa her şey son haliyle görünür. Gizleme yalnız kökteki `js` sınıfıyla devreye girer.

## Üç sahne

Modüller `brand/js/sahne/` altındadır.

- **Kendini kuran yazı** (`yazi-kur.js`): kimlik anı. Açılışta logo ve ilk başlık, gerçek glif geometrisinden (`brand/font/glifler.json`) kurulur. Oturumda bir kez. Sayfa yalnız kurduğu harfleri yükler: örnek sayfanın alt kümesi `brand/ornek/glifler.json`dır, `python brand/build.py` yazar ve sayfa onu `preload` ile erkenden ister. Glifler açılıştan 400 ms sonra hâlâ gelmemişse kurulum yapılmaz; okunmaya başlanmış başlık silinmez.
- **Çizgi ve söz** (`cizgi-soz.js`): logonun çizgi ve söz biçimi arasında bir kez geçiş. Logo tanıtılırken kullanılır.
- **Kurul turu** (`kurul-turu.js`): "nasıl çalışır" bölümü. Kaydırma sahnenin zamanıdır, altı adımda amblemi, altı özelliği ve hafızanın nasıl çalıştığını anlatır.

Sahnelerin yazıları kodda değil, `brand/js/metin.json`dadır. `tr` ve `en` aynı anahtarları taşır: `cizgiSoz` söz biçiminin sözlerini, yerleşimini (sözün yolda kaç kez tekrarlandığı, harf aralığı) ve iki biçimin erişilebilir adını; `kurulTuru` atla bağlantısını, etiketleri ve kayıt satırlarını tutar (`{yolda}`, `{tamam}`, `{denemede}` o durumdaki özellik sayısıyla dolar). Özellik adlarının İngilizcesi `ozellikler.json`daki `en` alanındadır. Söz biçiminin durağan SVG'leri `node brand/js/parca.mjs <tr|en>` ile üretilir. Bir dilin sözü değişirse yerleşimi yeniden ölçülür: yazı yolunu tam doldurmalı, taşmamalı; `tests/test_brand_js.py` bunu Chrome'da denetler.

Hareket yalnız bir şey anlatacaksa eklenir; süs için sahne konmaz.

## Simgeler

`brand/simge/` altında 30 simge. 24 birimlik ızgara, 2 birim çizgi, düz uçlar, `currentColor`. Yalnız halka parçası, düz çubuk ve eğik çubuk kullanılır. 45° yalnız "dışarı, çıkış, git" anlamındadır. Kaynak `build_simge.py`, dosyalar elle düzenlenmez.

## Amblem ailesi

C ve kor halka her üründe aynıdır, ortadaki işaret ürünü söyler: hafızada dalga, Kasa'da anahtar deliği. Yeni ürün işareti `brand/logo/amblem.py` içinde tek tanımla eklenir ve onaya sunulur. Ortadaki işaret 24 piksellik ürün simgesi olarak da kullanılabilir. Logo dosyaları (`brand/logo/`) değişmez.

## Altı parça ve ozellikler.json

Dış halkanın altı parçası sistemin altı temel özelliğidir. Bugünkü durumları tek yerden okunur: `brand/js/ozellikler.json`.

- Hafıza dolu, kişisel gelişim denemede, dört parça yolda.
- Bir özellik testlerini ve ölçümlerini geçince eklenir. Yeni özellik eklenince yalnız bu liste değişir.
- Altısı dolunca sürüm 1.0.0 çıkar.

## Nasıl üretilir

Depo kökünden:

```
python brand/build.py                    # tokens.json -> brand/css/tokens.css, karşıtlığı denetler; örnek sayfanın glif alt kümesi
python brand/simge/build_simge.py        # simgeler
python brand/logo/build_logo.py          # logo SVG'leri (font sanal ortamının python'u gerekir)
python brand/font/build_font.py          # Council Halka (font sanal ortamının python'u gerekir)
python docs/assets/build.py              # README görselleri (font sanal ortamının python'u gerekir)
```

Yazı tipi araçları (fontTools, skia-pathops, brotli) kalıcı kurulmaz; geçici bir sanal ortamda çalışır. Bir kez kurulur:

```
python3 -m venv ~/.cache/council-brand-venv
~/.cache/council-brand-venv/bin/pip install fonttools skia-pathops brotli pytest
```

Font, logo ve README görseli komutları bu ortamın python'uyla çalıştırılır:

```
~/.cache/council-brand-venv/bin/python brand/font/build_font.py
~/.cache/council-brand-venv/bin/python brand/logo/build_logo.py
~/.cache/council-brand-venv/bin/python docs/assets/build.py
~/.cache/council-brand-venv/bin/python -m pytest tests/test_brand_font.py tests/test_brand_logo.py -q
```

Üretim komutları çıktıyı değiştirmemelidir: değiştiriyorsa kaynak ile dosya ayrışmıştır. `build_font.py` da buna uyar: `head` tablosunun oluşturma ve değişiklik zamanı sabittir (`STAMP`), yazı tipi her üretimde birebir aynı çıkar. Logo SVG'leri de her seferinde birebir aynı çıkar.

## Nasıl denetlenir

```
python -m pytest -q                      # bütün testler, içerik taraması dahil
node --test tests/js                     # sahne mantığı
python brand/denetle.py <klasör>         # örnek sayfanın ekran görüntüleri ve taşma ölçümü
```

- `brand/denetle.py` Chrome ile örnek sayfaya (`brand/ornek/index.html`) açık, koyu, 375 ve 1280 piksel genişlikte, hareketi azaltma açık ve JavaScript kapalı bakar.
- İçerik taraması `brand/` altında araç adı ve kişisel bilgi arar; ikisi de sıfır olmalıdır. Örnek metinler geneldir ("toplantı kararı", "proje notu").

## Tasarım sistemi sayfası

claude.ai tasarım sistemi sayfası bu klasörden üretilir ve yalnız okunur. Sayfa elle düzenlenmez; değişiklik `tokens.json` ve `brand/` dosyalarında yapılır, sayfa aynı adresin üstüne yeniden yayınlanır.
