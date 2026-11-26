# COUNCIL tanıtım sitesi 1.0

**Durum:** onaylandı (2026-11-26 10:56, Claude'un kararlarıyla birlikte), yapıldı (2026-11-26 13:10; `4af1d9c..b0cbe2b`, sahip önizlemeyi onayladı, main'e yerelde birleştirildi; GitHub'a gönderilmedi, sunucuya yayınlanmadı). Yapımcı okumasından (üç bakış) çıkan sorular belgeye işlendi; Claude'un kararları "(Claude'un kararı)" diye işaretli.
**Kaynak:** proje sahibinin istekleri ve kararları (2026-11-26 00:56, 10:42–10:52). Görünüşün kuralları `docs/tasarim/2026-11-26-tasarim-sistemi.md` belgesindedir; bu belge o kuralları tekrar etmez, onlara uyar.

## Amaç ve neden

COUNCIL bir çatı marka; bugün tek ürünü Hafıza. Tanıtımı şu an yalnız GitHub'daki README'de duruyor: SVG kapak, SVG bölüm başlıkları, bir akış çizimi ve on bölüm, Türkçe ve İngilizce iki kopya.

Sahibin sözüyle sitenin üç işi var:

1. COUNCIL markasını insanlara tanıtmak.
2. Yapılan arayüzü (tanıtımı) GitHub dışına taşımak.
3. İleride COUNCIL ekosistemi adına yapılacak ürünlerin tanıtımlarını da bu sitede yapmak.

Başarı: Hafıza'yı hiç duymamış biri ana sayfada ne olduğunu bir dakikada anlar ve kurulum cümlesini kopyalar. İkinci ürün geldiğinde site baştan kurulmaz; ürünler şeridine bir öğe ve bir ürün sayfası eklenir.

## Proje sahibinin kararları

1. Önce tasarım sistemi, sonra site (00:52). Tasarım sistemi 0.2 yapıldı ve main'e birleştirildi (10:30).
2. Site **Türkçe + İngilizce**, aynı yapıda, dil değiştirme düğmesiyle (10:43).
3. Ana sayfa **"Marka + Hafıza"**: açılışta COUNCIL kimliği, ardından Hafıza'nın hikâyesi ve kurulum çağrısı, altta ürünler şeridi. Ayrıntı Hafıza sayfasında (10:45).
4. **Kasa ürünler şeridinde görünmez.** Arşivde; yeniden başlayınca eklenir (10:46).
5. Sayfa yapısı aşağıdaki haliyle onaylandı ("Uygun, devam", 10:51).
6. **Yapım yolu: depoda küçük bir Python üretici** (10:52). Elenenler: elle yazılmış HTML (iki dil zamanla birbirinden kopar, değerler sayfalara yazılır), hazır site çatısı (Python deposuna Node yükü, dört sayfa için fazla, hazır şablon görünümüne kayma), ayrı barındırma (kök adres taşınır, yardımcı bağlantıları bozulur).

Geçerliliğini koruyan eski kararlar: tanıtımda ve görsellerde araç adları geçmez, adlar yalnız ayrı bir "desteklenen yardımcılar" bölümünde geçer (2026-11-21); örnek içerikte kişisel bilgi yok; hazır yapay zekâ şablonu görünümü yok; logo değişmez.

## Hedefler

- Dört sayfa: ana sayfa ve Hafıza sayfası, her biri Türkçe ve İngilizce.
- Bütün görünüş `brand/` dosyalarından gelir; sitede renk, ölçü, yazı tipi ayarı ya da logo çizimi tutulmaz.
- İki dil tek şablondan üretilir; bir dilde olup ötekinde olmayan bölüm, bağlantı ya da metin anahtarı derlemede hata verir.
- Site dışarıya istek atmaz (yazı tipi, betik, sayaç yok). Tek dış bağlantılar GitHub'a gider.
- Araç adı ve kişisel bilgi denetimi siteyi de tarar.
- Arama motorlarına açık: başlık, açıklama, dil eşleri, paylaşım görseli, site haritası.
- `council.systems/` adresinde, sunucu koduna dokunmadan yayınlanır; `/mcp`, `/login`, `/.well-known/…`, simge adresleri ve `/panel/` çalışmaya devam eder.

## Kapsam dışı

- Kasa ya da başka ürün sayfası (şablon hazır olur, sayfa yapılmaz).
- Panelin yeni tasarım sistemine geçirilmesi (ayrı iş).
- README'nin kısaltılması ya da siteye yönlendirmesi (ayrı karar, aşağıda "Açık konular").
- Ziyaretçi sayacı, çerez, form, bülten.
- Kendi sunucusunda COUNCIL kuran kullanıcıların `/` sayfası. Site yalnız council.systems içindir; ürünle dağıtılmaz. `council/server.py` içindeki düz karşılama sayfası olduğu gibi kalır.

## Engeller (kaçınılacaklar)

- Tasarım sisteminin "kaçınılacaklar" listesinin tamamı (oval düğme, yuvarlak kart, yapay zekâ şablonu görünümü, siteyi yavaşlatan hareket).
- Desteklenen yardımcılar bölümü dışında herhangi bir yerde araç adı: metinde, görselde, sayfa başlığında, paylaşım görselinde, alternatif metinde.
- Sahibin adı ya da kişisel bilgisi. Alt bilgide "© 2026 COUNCIL · MIT lisansı" yazar, ad yazmaz.
- GitHub'daki eski bilgiyi aynen taşımak: README "sekiz araç" diyor, sunucu 12 araç kaydediyor (8 temel + 4 kişisel gelişim). Site doğru sayıyı yazar; sayılar ve sürüm tek kaynaktan gelir (aşağıda).

## Sayfa yapısı (onaylı)

### Ana sayfa — `/` ve `/en/`

```
┌ COUNCIL ─────────────────────── Hafıza · GitHub · TR/EN ┐
│  [logo ve başlık kendini kurar]                         │
│  Tek hafıza, bütün yardımcılar.                         │
│  [ Kurulum cümlesini kopyala ◸ ]   GitHub →             │
├─ Çizgi ve söz: "birçok üye · tek hafıza" → "ortak" ─────┤
├─ Ne işe yarar: 3–4 kısa madde ──────────────────────────┤
├─ Kurul turu (kaydırmalı): altı parça, Hafıza dolu,      │
│  kişisel gelişim denemede, dördü yolda → 1.0.0          │
├─ Ürünler: [dalga amblemi] Hafıza → ─────────────────────┤
└─ alt bilgi ─────────────────────────────────────────────┘
```

1. **Üst şerit** (`c-gezinme`): logo, "Hafıza", "GitHub", dil düğmesi.
2. **Açılış:** kimlik anı (Kendini kuran yazı) logo ve başlığı kurar. Altında bir cümlelik tanım. Ana eylem kurulum cümlesini kopyalayan kor düğme (ekrandaki tek kor), yanında ikincil "GitHub" bağlantısı. Kopyalanan cümle README'deki kurulum cümlesidir; araç adı içermez.
3. **Çizgi ve söz** sahnesi.
4. **Ne işe yarar:** 3–4 madde (yeni oturum sıfırdan başlamaz; düzeltmeler kural olur; bütün cihazlar tek hafızayı paylaşır; hafıza açık metin ve her değişiklik kayıtlı). Madde başına bir simge, kart değil.
5. **Kurul turu** sahnesi (altı hikâye adımı: Amblem, Altı özellik, Hafıza, Kişisel gelişim, Yolda, 1.0.0; "Hikâyeyi atla" bağlantısıyla).
6. **Ürünler şeridi:** bugün tek öğe, Hafıza (dalga amblemi, bir cümle, sayfasına bağlantı). Öğeler bir veri listesinden gelir.
7. **Alt bilgi:** küçük logo, GitHub, lisans, dil.

Ana sayfada iki sahne vardır (sınır iki); kimlik anı sahne sayılmaz.

### Hafıza sayfası — `/hafiza/` ve `/en/memory/`

Ürün sayfası şablonu. Açılışta amblem kimlik anındaki sırayla kurulur (tasarım sistemi kuralı), sonra bölümler:

1. Nasıl çalışır: üç oturum, tek hafıza. Hareketsiz çizim (README'deki akış çiziminin site sürümü, gerçek metinle).
2. Kurulum: üç yol (yardımcıya tek cümle; macOS/Linux komutu; Windows komutu), her biri kopyala düğmesiyle. Seçenekler ve komutlar kısa tablo.
3. İlk 5 dakika: dört adım.
4. Hafızanın içi: dosya düzeni.
5. Ölçümler: README'deki değerler, tarihi ve küçük örneklem uyarısıyla.
6. Neden farklı.
7. **Desteklenen yardımcılar:** araç adlarının geçtiği tek bölüm. Tablo bir veri dosyasından gelir.
8. Sık sorulanlar (`<details>`; JS gerekmez).
9. Belgeler: GitHub'daki belgelere bağlantılar.

Hafıza sayfasında sahne yoktur.

## Yapım (Claude'un tasarımı, sahibin seçtiği yol üzerine)

### Dosya düzeni

```
site/
  build.py          # üretici: python site/build.py → site/cikti/
  sablon/           # sayfa şablonları (string.Template ya da Jinja değil; aşağıya bkz.)
  metin/tr.json     # Türkçe metinler
  metin/en.json     # İngilizce metinler (aynı anahtarlar)
  veri/urunler.json       # ürünler şeridi (bugün yalnız Hafıza)
  veri/yardimcilar.json   # desteklenen yardımcılar tablosu (araç adlarının tek izinli yeri)
  cikti/            # üretilen site (depoya girer; yayın buradan yapılır)
  yayinla.sh        # cikti/ → sunucu (sahibin onayıyla çalıştırılır)
  README.md         # nasıl üretilir, önizlenir, yayınlanır
tests/test_site_*.py
```

- **Şablon dili:** Python'un kendi `string.Template`'i ya da küçük bir yer tutucu değiştirici; yeni bağımlılık eklenmez. Döngü gereken yerler (madde listeleri, tablolar) `build.py` içinde HTML parçası olarak üretilir. Kesin biçimi yapımcı seçer.
- **Tek kaynaktan gelenler:** renk, ölçü, bileşenler `brand/css/`; yazı tipleri `brand/font/`; logo ve amblemler `brand/logo/`; simgeler `brand/simge/`; sahneler `brand/js/sahne/`; özellik durumu `brand/js/ozellikler.json`; sürüm `pyproject.toml`; araç sayısı `council/server.py` kaynağından (derlemede `@mcp.tool` sayılır, sunucu içe aktarılmaz, elle yazılmaz). Site "8 temel araç + 4 kişisel gelişim aracı (denemede)" diye yazar; kişisel gelişim araçları `council_rule`, `council_skill`, `council_skill_feedback`, `council_unlearn` adlarıyla ayrılır (Claude'un kararı: özellik durumuyla tutarlı). `build.py` bunları `cikti/varlik/` altına aynı göreli düzende kopyalar (yazı tipi yolları `../font/` olduğu için `css/` ve `font/` kardeş kalır).
- **Çıktı adresleri:** `cikti/index.html`, `cikti/hafiza/index.html`, `cikti/en/index.html`, `cikti/en/memory/index.html`, `cikti/varlik/…`, `cikti/sitemap.xml`, `cikti/robots.txt`, paylaşım görselleri. Önbellek kırma için varlık adlarına içerik özeti eklenir.
- **Derleme tekrarlanabilir:** aynı girdi aynı baytları üretir (tarih damgası yok). Derleme sonrası `git status` temiz kalır.
- **Paylaşım görseli:** dil başına 1200×630 PNG, Council Halka yazısıyla. Önce SVG olarak üretilir, sonra `denetle.py`'nin zaten kullandığı başsız Chrome ile PNG'ye çevrilir (yeni bağımlılık yok; Claude'un kararı). PNG depoya girer, normal derleme yeniden üretmez.

### Dil

- **`brand/` içinde yapılacak dil değişikliği (Claude'un kararı).** Sahnelerdeki sabit Türkçe metinler (`cizgi-soz.js` sözleri, `kurul-turu.js` "Hikâyeyi atla" ve adım adları) ve `ozellikler.json` içindeki adlar ve açıklamalar yalnız Türkçe. İngilizce sayfalar için sahneler metni sayfadan alır (`data-` öznitelikleri ya da `baslat()` seçeneği; verilmezse bugünkü Türkçe kalır), `ozellikler.json` her özelliğe `en` alanları kazanır. Bu, tasarım sisteminde küçük bir değişikliktir; `tests/test_brand_*` ve `tests/js/` testleri buna göre genişler, sahne dosyası 15 KB sınırı korunur (`kurul-turu.js` sınıra yakın; metin taşımak dosyayı küçültür). Görünüşe dokunulmaz.

- `/` Türkçe, `/en/` İngilizce. Tarayıcı diline göre kendiliğinden yönlendirme yok (adres her zaman aynı içeriği verir).
- Her sayfada `hreflang` eşleri ve karşı dildeki aynı sayfaya giden dil düğmesi.
- `metin/tr.json` ve `metin/en.json` anahtarları birebir aynı olmak zorunda; eksik ya da fazla anahtar derlemeyi durdurur.

### Hareket ve erişilebilirlik

Tasarım sisteminin hareket kurallarına uyar: kimlik anı oturum başına bir kez, en çok 1,8 sn, ilk ekran metni 1,2 sn içinde okunur; sahneler tek sefer, boştayken sıfır kare; `prefers-reduced-motion` ve JS yokken tam anlamlı durağan hal. Kopyala düğmesi JS yoksa cümleyi seçilebilir metin olarak gösterir. Klavye ile bütün bağlantılara ulaşılır, odak halkası görünür.

### Denetim (testler)

- Araç adı ve kişisel bilgi taraması `site/` altındaki her şeyi (kaynak ve çıktı) tarar; tek istisna `veri/yardimcilar.json` ve ondan üretilen tablo bölümü (çıktıda işaretli bir bölüm, tarama o bölümü atlar). Kelime listeleri bugün `tests/test_brand_icerik.py` içinde; tek kaynak olması için `brand/` altında küçük bir modüle taşınır ve iki test oradan okur (Claude'un kararı).
- GitHub kullanıcı adı: depo adresi (`github.com/<kullanıcı>/council`) ve kurulum cümlesi kullanıcı adını içerir. Depo herkese açık olduğu için bu adres sitede geçer; tarama yalnız bu tam adres biçimine izin verir. Sahibin adı ve soyadı açık yazıyla hiçbir yerde geçmez (Claude'un kararı).
- İki dil anahtar eşliği; her sayfada başlık, açıklama, `lang`, `hreflang`.
- İç bağlantıların hepsi var olan bir dosyaya gider; dış bağlantılar yalnız `github.com` ve `raw.githubusercontent.com`.
- Dış kaynak yok: `<script src>`, `<link href>`, `url()` ve `@import` yalnız göreli adres.
- Sayfa başına en çok iki sahne; Hafıza sayfasında sıfır.
- Renk değeri yok: site kaynaklarında ve üretilen HTML'de onaltılık renk ya da `rgb(` geçmez (tasarım sistemi kuralı). `brand/`'dan kopyalanan dosyalar (`varlik/` altındaki `tokens.css`, SVG'ler) taramadan çıkar; onlar tasarım sisteminin kendi testleriyle denetlenir.
- Tarayıcı denetimi: `brand/denetle.py` bugün yalnız `brand/ornek/index.html`'i ölçer. Sayfa yolunu parametre alacak biçimde genelleştirilir (Claude'un kararı); site sayfaları aynı `?denetim=1` ölçüm kancasını taşır. Masaüstü ve 375 px'te taşma yok, sahneler çiziliyor, konsolda hata yok.
- Derleme iki kez çalıştırılınca çıktı bayt bayt aynı.
- Ağırlık bütçesi: ana sayfanın ilk yüklemesi (yazı tipleri hariç, sıkıştırılmış) 250 KB'ı geçmez.

### Önizleme

- Yerel: `.claude/launch.json` içine `council-site` (http.server, `site/cikti`).
- Sahibin bakışı: çıktı claude.ai'de özel sayfa olarak yayınlanır; sahip masaüstünde ve telefonda bakar.

### Yayın (ayrı adım, sahibin onayıyla)

0. Betik yazılmadan önce sunucudaki gerçek Caddy ayarı, `--public-host` değeri ve SSH erişimi salt okunur biçimde incelenir (depodaki `deploy/Caddyfile` yalnız örnek). Aşağıdaki adres listesi ve geri alma bu incelemeye göre kesinleşir.
1. `site/yayinla.sh` çıktıyı SSH ile sunucuda `/var/www/council-site/surumler/<commit>/` klasörüne kopyalar, sonra `/var/www/council-site/guncel` bağlantısını yeni klasöre çevirir (tek adımda geçiş). Son üç sürüm saklanır; eski HTML'in istediği varlıklar silinmez. Site ürün sürümlerinden bağımsız yayınlanır.
2. Sunucunun Caddy ayarına bir kez, mevcut yönlendirmenin önüne bir blok eklenir: `/`, `/en`, `/en/*`, `/hafiza`, `/hafiza/*`, `/varlik/*`, `/sitemap.xml`, `/robots.txt` ve paylaşım görselleri dosyadan sunulur; geri kalan her şey (bugünkü gibi) `/panel*` → panel, diğerleri → hafıza servisi. Örnek blok `site/README.md` içinde durur; depodaki `deploy/Caddyfile` (kendi sunucusunu kuranlar için örnek) değişmez.
3. Yayından sonra denetim: dört sayfa 200 döner; `/mcp`, `/login`, `/.well-known/oauth-authorization-server`, `/health`, `/icon.svg`, `/panel/` önceki gibi yanıt verir; bir yardımcı bağlantısıyla hafıza okunur.
4. Geri alma: içerik hatasında `guncel` bir önceki sürüme çevrilir. Kurulum hatasında Caddy bloğu silinip yeniden yüklenir (`caddy validate` sonra `reload`); `/` eski düz sayfaya döner.

Her yayın (ilk kurulum ve sonraki güncellemeler) sahibin açık onayıyla yapılır. Depoyu GitHub'a göndermek ayrı onaydır.

## Yapımcıya bırakılanlar

- Metinlerin kesin hali (README'den kısaltılarak; sahip önizlemede okur).
- Başlıklarda büyük/küçük harf: Claude'un önerisi, logo ve bölüm etiketleri büyük harf, büyük başlıklar cümle düzeninde. Sahip önizlemede görür.
- Şablon yer tutucularının biçimi, varlık adlarındaki özet uzunluğu, site haritası ayrıntıları.
- Hafıza sayfasındaki akış çiziminin kesin çizimi (tasarım sisteminin çizgi ve renk kurallarıyla).

## Açık konular (sahibin kararı)

- README'nin geleceği: site yayına girince README kısaltılıp siteye mi yönlendirilsin, yoksa olduğu gibi mi kalsın? Bu projeye girmez; yayından sonra ayrıca sorulur.
