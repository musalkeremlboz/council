# COUNCIL tasarım sistemi 0.2

**Durum:** onaylandı (2026-11-26 02:38). Kod yazılmadı.
**Kaynak:** proje sahibinin istekleri ve kararları (2026-11-26 00:52 – 02:32). Görünüş ve hareket, sahibin onayladığı denemelere dayanır; denemelerin kopyaları `2026-11-26-tasarim-sistemi-ekler/` klasöründedir ve bu belge her birini ayrıca yazıyla anlatır.
**Önceki sürüm:** Tasarım sistemi 0.1 (2026-11-17). claude.ai'de özel bir tasarım sistemi sayfası olarak yayınlandı; onaylanmadı. Bu belge 0.1'in yerini alır.

## Amaç ve neden

COUNCIL bir çatı marka. İlk ürünü hafıza, ikinci ürünü Kasa (şifre yöneticisi, arşivde). Sırada bir tanıtım sitesi var. Sitenin üç işi olacak: markayı insanlara tanıtmak, şu an yalnız GitHub'da duran tanıtımı oradan çıkarmak, ileride ekosistemin ürünlerini de tanıtmak.

Site birden çok ürünü taşıyacağı için tasarım sisteminin baştan netleşmesi gerekiyor. Sahibin sözüyle: tuşlar, animasyonlar, renkler ve bütün öğeler. Bugün sistemin parçaları dağınık. Renkler `council/panel/static/panel.css` içinde duruyor, yazı tipi ve logo `brand/` altında, kurallar ise onaylanmamış 0.1 sayfasında. Panelin düğmeleri sıradan oval haplar. Sahibin istediği ise bunun tersi. Sözü: "butonlar normal site butonları gibi oval biçimde olmasın... bize özgü, eşsiz bir yönü bulunmalı."

Bu belge sistemi tarif eder. Site ayrı bir projedir ve bu sistem bittikten sonra yapılacaktır.

## Proje sahibinin kararları

Bu oturumdaki kararlar:

1. Önce tasarım sistemi kurulur, site sonra yapılır. Mevcut sistem geliştirilebilir (00:52).
2. Sitenin amacı: markayı tanıtmak, arayüzü GitHub dışına taşımak, ileride ekosistem ürünlerinin tanıtımını yapmak. Bu yüzden tasarım sistemi en baştan tamamen netleşmeli (00:56).
3. **Düğme imzası "Tek Kesik"** (01:27). Üç seçenek arasından seçildi; Açık C ve Eksik Çeyrek elendi.
4. **Council Halka'ya küçük harf eklenecek** (01:29). İki seçenek elendi: yalnız büyük harfle kalmak ve tam bir metin ailesi kurmak.
5. Sitede düğmeler dışında da hareket olacak. Sahibin örnekleri: aşağı kaydırdıkça değişen arayüz, sürekli farklı biçimde görünen logo (ASCII, tek çizgi, piksel vb.) (01:32).
6. Denemelere geri bildirim (02:08):
   - "Kendini kuran yazı" beğenildi.
   - Yaşayan logoda yalnız asıl çizim ve sözcüklerden kurulan biçim kalacak.
   - Kurul turunda halkanın parçaları cihazları değil, sistemin özelliklerini temsil edecek.
7. Hareket dili ikinci turdaki haliyle onaylandı ("Uygun, devam", 02:30).
8. **Yapım yolu: kod deposu tek kaynak** (02:32). claude.ai'deki tasarım sistemi sayfası koddan üretilir.

Önceki oturumlardan gelen ve geçerliliğini koruyan kararlar:

- Renk paleti "Kor": mürekkep `#111416`, zemin `#F4F5F3`, vurgu `#E8421F` (2026-11-17).
- Logo ve yazı tipi Council Halka onaylı (2026-11-17). Logo değişmez.
- Logoda sabit olanlar: halka düzeni ve kesme biçimi. Sahip O harfinin renkli olmasını seviyor (2026-11-17).
- Amblem ailesi (2026-11-17, Kasa): C ve kor halka her üründe aynı kalır, ortadaki işaret ürünü söyler. Hafızada bu işaret dalga, Kasa'da anahtar deliği.
- Dış halkanın altı parçası sistemin altı temel özelliğidir (2026-11-21):
  - İlki hafıza ve dolu.
  - Diğerleri temel özellikler eklendikçe dolar.
  - Altısı dolunca sürüm 1.0.0 çıkar.
  - Bir özellik ancak testlerini ve ölçümlerini geçtiğinde eklenir.
- Tanıtım sayfasında ve görsellerde belirli araç adları (yardımcı ürünlerinin adları) geçmez. Adlar yalnız ayrı bir "desteklenen yardımcılar" bölümünde geçer (2026-11-21).
- COUNCIL uygulamalarında tıklayınca açılan her şey uygulamanın kendi arayüzüne uyar. Animasyonlar akıcı olmalı; yarıda takılan geçiş kusurdur (2026-11-18).

## Hedefler

- **Tek kaynak.** Bütün tasarım değerleri, stiller, bileşenler, hareket kodu, yazı tipi, logo ve simgeler `brand/` altında durur. Site, panel ve ileride Kasa aynı dosyaları kullanabilir. Hiçbir değer iki yerde tutulmaz.
- **Tek Kesik düğme dili** bütün bileşenlere tutarlı bir dilbilgisiyle yayılır.
- **Council Halka 0.2:** küçük harfler, Türkçe küçük harfler ve temel harf çifti aralıkları eklenir. Büyük harfler ve logo değişmez.
- **Hareket dili** üç katmanda tanımlanır: arayüz, kimlik anı, sahne. Onaylanan üç sahne yeniden kullanılabilir modüllere çevrilir.
- **Simge seti:** ilk aşamada yaklaşık 30 simge, aynı ilkelerle çizilir.
- **Marka kitabı:** Türkçe README. Her değerin ne zaman kullanılacağı orada yazar.
- **Canlı örnek sayfası:** her bileşen ve sahne açık temada, koyu temada ve telefon genişliğinde görülür. Sahip sistemi bu sayfadan bakarak anlar.
- **claude.ai tasarım sistemi sayfası** koddan üretilir ve yalnız okunur. Sahip orada gezinip yorum bırakabilir.

## Kapsam dışı (bu projede yapılmayacak)

- Tanıtım sitesinin kendisi. Bu sistemin üstüne kurulacak ayrı bir projedir ve sıradaki iştir.
- Panelin yeni sisteme geçirilmesi: oval düğmeler, 6 ve 12 piksellik köşeler. Ayrı bir iştir.
- Kasa uygulaması.
- Council Halka'ya birden çok kalınlık eklemek ya da okuma metni için kullanmak. Okuma metni DM Sans olarak kalır.
- Elenen sahneler:
  - "Kesik hattı": bölümler arasında 45° kesikli geçiş.
  - "Kurul masası": canlı not akışı.
  - "Kurula katıl": ziyaretçinin not bırakması. En özgün fikirdi ama telefonda çalışmıyordu. İleride ayrı bir "kendin dene" sayfası olarak yeniden düşünülebilir.
- İngilizce marka kitabı. Metinler tek yerde toplanır ki sonradan çevrilebilsin.

## Olmaması gerekenler

- Oval ya da hap biçiminde düğme, yuvarlatılmış köşeli kart. 6 ve 12 piksellik köşelerden hiçbiri kalmaz.
- Hazır şablon ya da yapay zekâ şablonu görünümü: renk geçişli arka planlar, gölgeli kartlar, emoji kartları, sol kenarı çizgili kartlar.
- Siteyi yavaşlatan hareket. Sonsuz döngü, sayfa boştayken çizilen kare, ilk ekranı animasyon bitene kadar gizlemek. (Daha önce başka bir sitede animasyonların siteyi yavaşlattığı yaşandı.)
- Görsellerde ve örnek metinlerde araç adları.
- Örnek içerikte kişisel bilgi: randevu, sınav, sağlık, borç, gerçek kişi adı. Örnekler genel olur ("toplantı kararı", "proje notu"). Depo ileride herkese açılabilir.
- Aynı değerin iki yerde tutulması. claude.ai sayfasında elle düzenleme de buna dahildir.
- Bir ekranda birden fazla kor öğe.

## Kısıtlar

- Saf HTML/CSS/SVG ve sade JavaScript. Dış kütüphane, çerçeve ya da paketleyici kullanılmaz. Üretim betikleri depodaki mevcut düzene uyar: Python, yazı tipi için fonttools, skia-pathops ve brotli. Bu araçlar geçici bir sanal ortamda kurulur, kalıcı bağımlılık olmaz.
- Yazı tipi dosyaları yerelde durur. DM Sans ve DM Mono (OFL lisanslı) zaten `council/panel/static/fonts/` altında var. Google Fonts'a bağlanılmaz. Bunun iki sebebi var: site dışarıya istek atmasın ve hızlı açılsın (Claude'un kararı).
- Erişilebilirlik:
  - Metin karşıtlığı her temada en az 4.5:1 olur. 24 piksel ve üstündeki yazılarda, kontrol kenarlarında ve odak çizgisinde 3:1 yeter.
  - Dokunma hedefi en az 44 piksel olur.
  - Klavye odağı her zaman görünür.
  - `prefers-reduced-motion` açıksa her sahnenin durağan ve anlamı eksiksiz bir karşılığı vardır.
  - `forced-colors` (yüksek karşıtlık) açıkken düğmeler düz çerçeveye düşer.
  - JavaScript yoksa her şey son haliyle görünür.
- Tarayıcılar: Chrome, Safari ve Firefox'un güncel sürümleri, telefon dahil. `@property` ve View Transitions gibi yeni özellikler yalnız süs içindir. Desteklenmeyen tarayıcıda işlev bozulmaz, yalnız geçiş anında olur.
- Logo dosyaları (`brand/logo/`) ve Council Halka'nın büyük harf glifleri değişmez. Yazılı logo bu gliflerle dizilmiştir.

## Yaklaşımlar

Üç yol düşünüldü:

- **A · Kod deposu tek kaynak, tasarım sayfası koddan üretilir (seçilen).** Sistem `brand/` altında yaşar. Site, panel ve Kasa aynı dosyayı kullanır. claude.ai'deki tasarım sistemi sayfası bir betikle koddan yeniden üretilir ve "koddan eşitlenir" olarak işaretlenir, böylece elle düzenlenemez. Bedeli: kurulum biraz daha uzun. Sahip bu yolu seçti. Sebep, ekosistemin büyüyeceği ve tek kaynağın bunu taşıyan tek sağlam yol olması.
- **B · claude.ai tasarım sistemi sayfası kaynak olur.** Gezinmesi ve yorum bırakması kolay. Ama site ve panel yine kod ister; aynı değerler iki yerde tutulur ve zamanla birbirinden kayar. Elendi.
- **C · Her ürün kendi stilini tutar.** Bugünkü durum (panel kendi CSS'ini taşıyor). Ekosistem büyüdükçe ürünler birbirinden uzaklaşır. Baştan elendi.

## Sistem

### Temel fikir

Logonun bütün parçaları tek kuraldan çıkar: tam bir halka alınır ve düz bir kesimle kesilir. Sistem bu iki hareketi işe bağlar:

> **Halka durumu söyler, kesik eylemi söyler.**

- Tıklanabilen her öğenin sağ üst köşesinde tek bir 45° kesik vardır. Tıklanamayan hiçbir şeyde kesik olmaz. Kullanıcı neye basabileceğini biçimden öğrenir.
- Bekleyen, çalışan, biten ve hafızaya yazılan durumlar halkayla gösterilir.
- Köşe ya sıfırdır, ya tam dairedir, ya da 45° kesiktir. Başka köşe olmaz. Gölge ve renk geçişi yoktur.

Kesik, Council Halka'daki C harfinin 45°'lik uç kesiğinden gelir. Sağ üstte durur, çünkü logodaki C'nin ağzı sağdadır: logoda içerideki şey dışarıya ağızdan bağlanır, düğmede de eylem ağızdan çıkar.

### Renk

0.1'deki renk değerleri aynen kalır (ikinci tablo). Tek Kesik için yeni değerler eklenir:

| Ad | Açık | Koyu | Kullanım |
|---|---|---|---|
| `murekkep-bas` | `#2E3438` | `#D3D7D2` | Basılan birincil düğmenin gövdesi |
| `kor-bas` | `#F25A38` | `#F25A38` | Basılan kor düğmenin gövdesi. Kor koyulaştırılmaz, yalnız açılır; koyu yazıyla 5,5:1 verir |
| `pasif-zemin` | `#E2E4E1` | `#23282B` | Devre dışı düğmenin gövdesi |
| `pasif-yazi` | `#5B6166` | `#9AA0A4` | Devre dışı düğmenin yazısı (4,8:1) |
| `ton` | `rgb(17 20 22 / .07)` | `rgb(244 245 243 / .08)` | İkincil ve hayalet düğmelerde üzerine gelince, basınca ve odakta beliren hafif dolgu |

0.1'den kalan değerler:

| Ad | Açık | Koyu |
|---|---|---|
| zemin | `#F4F5F3` | `#111416` |
| yuzey | `#FFFFFF` | `#1A1E21` |
| yuzey-2 | `#E9EBE8` | `#23282C` |
| murekkep | `#111416` | `#F4F5F3` |
| murekkep-2 | `#4A5157` | `#B4BBC0` |
| murekkep-3 | `#656D74` | `#8A9299` |
| cizgi | `#D5D8D4` | `#2E3438` |
| cizgi-guclu | `#848B91` | `#6A737A` |
| kor | `#E8421F` | `#E8421F` |
| kor-metin | `#C2330F` | `#FF7A5C` |
| kor-zemin | `#FBE4DD` | `#3A1A12` |
| kor-ustu | `#111416` | `#111416` |
| basari | `#1F7A4D` | `#4CC38A` |
| uyari | `#8A5A00` | `#E3B341` |
| hata | `#B3123F` | `#FF6B8B` |

Kurallar:

- Kor bir ekranda tek bir şeydir: hafıza (logodaki O), en önemli eylem ya da odaktaki öğe.
- Kor dolgunun üstündeki yazı her zaman koyu olur (`kor-ustu`), çünkü beyaz 4.5:1'i tutmaz.
- `hata` kor ile karışmasın diye pembeye çekik seçildi.
- Durum renkleri yalnız durum bildirir ve her zaman bir sözcükle birlikte kullanılır.

### Köşe

0.1'deki `kose-s` (6px) ve `kose-m` (12px) kaldırılır. Geriye üç değer kalır:

- `kose-0`: kartlar, alanlar, düğme gövdesi.
- `kose-tam`: halkalar, radyo düğmesi, rozetin yuvarlak yanı.
- `kesik`: 45° kesik. Ölçüsü bileşen yüksekliğinden hesaplanır, sabit bir sayı değildir.

### Yazı

| İş | Yazı tipi | Not |
|---|---|---|
| Başlık, logo, ürün adı | Council Halka | Markaya özel. 24 pikselin altında kullanılmaz. Paragraf dizilmez |
| Okuma metni ve arayüz | DM Sans | Yerel dosyadan yüklenir |
| Kod, komut, yol, kayıt satırı | DM Mono | Yerel dosyadan yüklenir |

0.1'deki yazı stilleri aynen kalır:

| Ad | Yazı tipi | Boy | Satır | Kalınlık | Harf arası | Kullanım |
|---|---|---|---|---|---|---|
| `baslik-xl` | Council Halka | 64px | 1.05 | 500 | 0.04em | Kapak başlığı, sayfada bir kez |
| `baslik-l` | Council Halka | 40px | 1.1 | 500 | 0.04em | Sayfa başlığı |
| `baslik-m` | Council Halka | 24px | 1.2 | 500 | 0.05em | Bölüm başlığı; Halka için en küçük boy |
| `etiket` | DM Sans | 12px | 1.3 | 600 | 0.08em | Büyük harfli küçük etiket |
| `govde-l` | DM Sans | 18px | 28px | 400 | — | Giriş paragrafı |
| `govde` | DM Sans | 16px | 24px | 400 | — | Varsayılan metin |
| `govde-k` | DM Sans | 14px | 20px | 400 | — | Yardımcı metin, tablo hücresi |
| `kod` | DM Mono | 14px | 22px | 400 | — | Komut, yol, kimlik |

Düğme yazıları kendi bölümündeki boyları kullanır (15/14/17px, 500). Küçük harf geldiği için başlıklar artık cümle düzeninde de yazılabilir. Hangi başlığın büyük harfle yazılacağına site tasarımında karar verilir. Küçük harfle dizilen Halka başlıklarında harf arası 0'a yakın olabilir; kesin değeri yapımcı örnek sayfada belirler.

### Boşluk

0.1'deki ölçek aynen kalır; ara değer uydurulmaz.

| Ad | Değer | Kullanım |
|---|---|---|
| `ara-1` | 4px | Simge ile yazısı arası |
| `ara-2` | 8px | Birbirine bağlı öğeler arası |
| `ara-3` | 12px | Alan içi dolgu, etiket ile alan arası |
| `ara-4` | 16px | Küçük kart dolgusu, telefon kenar boşluğu |
| `ara-6` | 24px | Kart içi dolgu, öğe grupları arası |
| `ara-8` | 32px | Bölüm içi bloklar arası |
| `ara-12` | 48px | Bölümler arası |
| `ara-16` | 64px | Sayfa açılışı ve büyük boşluklar |

### Hareket değerleri

| Ad | Değer |
|---|---|
| `sure-bas` | 70ms |
| `sure-tepki` | 140ms |
| `sure-panel` | 240ms |
| `sure-sahne` | 420ms |
| `sure-gecis-en-cok` | 840ms |
| `egri-ac` | cubic-bezier(.2,0,0,1) |
| `egri-kapa` | cubic-bezier(.4,0,1,1) |

### Council Halka 0.2: küçük harfler

- Her küçük harf büyük harflerle aynı üç ilkelden kurulur: düz çubuk, tam daireden kesilmiş halka parçası, eğik çubuk. Tek çizgi kalınlığı (1000 birimde 100), düz kesik uçlar.
- Kapsam: a–z, Türkçe küçük harfler (ç ğ ı i ö ş ü) ve i ile ı'nın doğru eşleşmesi. Şu an küçük harfler büyük harf biçimine gidiyor. 0.2'de her küçük harfin kendi glifi olur ve `İ/i`, `I/ı` eşlemeleri doğru kalır.
- Temel harf çifti aralıkları (kerning) eklenir: büyük-büyük, büyük-küçük, küçük-küçük. En azından yay ve çubuk komşuluklarında (ör. "LA", "To", "ro") açılan boşluklar kapatılır.
- Eksik işaretler eklenir: `& @ # % + = ( ) " ' ; …` ve ok.
- 45° kesik bazı küçük harflerde (ör. a, e, t) tekrar edebilir. Bu Claude'un önerisidir; okunurluğu bozuyorsa uygulanmaz.
- **Büyük harfler, rakamlar ve logodaki harfler değişmez.** Logo SVG'leri yeniden üretilirse bayt bayt aynı çıkmalıdır.
- Sürüm "0.2". Kaynak `brand/font/build_font.py`, çıktılar `.ttf` ve `.woff2`.

### Düğme: Tek Kesik

Ayrıntılı ve çalışan örnek: `2026-11-26-tasarim-sistemi-ekler/dugme-tek-kesik.html` ve `.css`.

- **Biçim:** dikdörtgen, köşe 0, sağ üstte tek bir 45° kesik. Kesik ölçüsü `k = yükseklik × 2/7`.
- **Boylar:**
  - Orta: 44 piksel yükseklik, k = 12 piksel. İç boşluk solda 20, sağda 26 piksel. Yazı DM Sans 500, 15 piksel. En dar 96 piksel.
  - Küçük: 32 piksel, k = 9 piksel, 14 piksel yazı. Yalnız fareli cihazda kullanılır; dokunmatikte kendiliğinden ortaya büyür.
  - Büyük: 56 piksel, k = 16 piksel, 17 piksel yazı. Sitede kullanılır.
- **Türler:**
  - Kor: dolgu kor, yazı koyu. Ekranda en fazla bir tane olur.
  - Birincil: mürekkep dolgu.
  - İkincil: 2 piksel çerçeve; çerçeve kesiği de izler.
  - Hayalet: yalnız metin, sağ üstte 3 piksel kalınlığında kısa bir 45° kesik çizgisi. Böylece düz metinden her zaman ayrılır.
- **Durumlar:**
  - Üzerine gelince: yalnız fareli cihazda, kesik 4 piksel açılır (140 ms). Renk değişmez.
  - Basınca: kesik 4 piksel kapanır (70 ms), gövde bir ton açılır (`murekkep-bas`, `kor-bas`).
  - Odak: klavye odağında 2 piksel `kor-metin` çizgi, 3 piksel uzakta. Çizgi sağ üstü açık bir C gibi düğmeyi sarar; iki ucu kesik çizgisinin uzantısında düz biter.
  - Devre dışı: kesik kapanır ve düğme düz bir kare olur (eylem yok, kesik yok). `pasif-zemin` ve `pasif-yazi` kullanılır. Mümkünse `aria-disabled` verilir ve nedeni yanına yazılır.
  - Yükleniyor: `aria-busy="true"`. Kesik sabit kalır, yazının sağında 16 piksellik dönen C görünür (bir tur 900 ms). 300 ms'den kısa işlerde gösterilmez.
  - Hafızaya yazıldı: kısa bir süre küçük bir kor O görünür (durum sözlüğüne bakınız).
- Sağdan sola yazılan dillerde kesik sol üste geçer.
- Yüksek karşıtlık modunda kesik kaybolur, yerine düz bir çerçeve gelir.

### Bileşenlerin dilbilgisi

Kural tektir: **tıklanıyorsa kesiği vardır, tıklanmıyorsa yoktur.**

| Bileşen | Biçim |
|---|---|
| Alan (metin girişi) | Köşe 0, kesik yok (veri alır, eylem yapmaz). 44 piksel yükseklik, `cizgi-guclu` çerçeve. Odakta düğmeyle aynı açık C çizgisi. Etiket her zaman görünür |
| Kart | Tıklanmayan kart düz bir karedir. Tıklanan kartta sabit bir kesik vardır (k = 24 piksel, üzerine gelince 32 piksel). Tıklanan kartın içine ikinci bir kesikli düğme konmaz |
| Rozet | Durum ve etiket bildirir, tıklanmaz, kesik almaz. 0.1'deki "sol yanı yuvarlak, sağ yanı düz" biçim kalır. İçinde 8 piksellik bir durum işareti, yanında her zaman sözcük vardır |
| Durum işareti | Açık C: hazır ya da bekliyor. Dönen C: çalışıyor. Tam O: tamam. Kor O: hafızaya yazıldı. Yarım halka: hata. Hareket azaltılmışsa çalışma durumu durağan 270°'lik bir C olarak gösterilir |
| İlerleme | Dairesel ilerlemede Halka bileşeni kullanılır, uçları düzdür. Doğrusal şerit 6 piksel kalınlıktadır ve ilerleyen ucu 45° kesiktir |
| Gezinme | Bağlantılar düz metindir. Bulunulan sayfanın solunda 6 piksellik dolu bir daire durur. Başlık çubuğundaki tek kor öğe eylem düğmesidir |
| Sekme | Seçili sekme, sağ üstü kesik bir yüzey bloğudur. Seçili olmayan sekmeler düz metindir |
| Açılır menü ve panel | Sağ üstten 45° bir çizgiyle açılır (clip-path, 240 ms). Uygulamanın kendi arayüzüyle çizilir, sistem menüsü kullanılmaz |
| İşaret kutusu ve radyo | İşaret kutusu kare, radyo düğmesi halkadır |
| Metin içi bağlantı | Kesik almaz; mürekkep renginde alt çizgiyle gösterilir. Kesik paragraf içinde gürültü yapar (Claude'un kararı) |

### Hareket

Üç katman vardır ve birbirine karışmaz. Bir ekranda aynı anda yalnız bir katman kendiliğinden hareket eder.

1. **Arayüz hareketi.** Her sayfada vardır, sakindir. Yalnız kesik ve halka hareket eder. Dört süre kullanılır: basma 70 ms, tepki (üzerine gelme, odak, renk) 140 ms, panel ve menü 240 ms, sayfa geçişi 420 ms. Eğriler: açılma ve geliş için `cubic-bezier(.2,0,0,1)`, kapanma ve gidiş için `cubic-bezier(.4,0,1,1)`, dönen her şey doğrusal. Ölçek değişimi, zıplama, gölge ve geri sekme yoktur.
2. **Kimlik anı.** Oturum başına bir kez, yalnız açılışta oynar. "Kendini kuran yazı" bu katmandadır.
3. **Sahne hareketi.** Anlatı içindir. Sayfa başına en fazla iki yerde, her biri kendi bölümünde kullanılır: "Çizgi ve söz" ile "Kurul turu".

Kurallar:

- **Ne zaman:** hareket yalnız bir şey anlatmak için eklenir: kurul, hafıza ya da marka anatomisi. Süs için hareket eklenmez.
- **Ne kadar:** kendiliğinden başlayan her sahne bir kez oynar ve durur. Sonsuz döngü yoktur. Kaydırmaya bağlı sahne en fazla 450vh sürer ve her zaman bir "atla" bağlantısı taşır.
- **Ne hareket eder:** yalnız halka, kesik ve dalga. Yakınlaşma, uzaklaşma, parlama ve opaklıkla yapılan süslü girişler kullanılmaz. Taşınan bilgi kor ile değil, zemin renginde bir kesikle gösterilir.
- **Süreler:** sahne geçişi en fazla 840 ms sürer. Kimlik anı en fazla 1,8 sn sürer ve ilk ekrandaki metin 1,2 sn içinde okunur olur. İlk ekrandaki içerik hiçbir zaman animasyon bitene kadar gizlenmez.
- **Hız bütçesi:**
  - Sayfa boştayken sıfır kare çizilir.
  - `requestAnimationFrame` yalnız bir değer hedefine yaklaşırken çalışır.
  - Ekran dışındaki sahne `IntersectionObserver` ile, arka plandaki sekme `visibilitychange` ile durdurulur.
  - Kaydırma dinleyicisi pasiftir ve yalnız sahne ekrandayken bağlıdır.
  - Kare başına en fazla bir ölçüm yapılır ve DOM'a yalnız değişen değer yazılır.
  - Sahne başına kod 15 KB'ı geçmez.
  - Canvas, filtre ve dış kütüphane kullanılmaz.
- **Hareketi azaltma:** her sahnenin durağan ve anlamı eksiksiz bir karşılığı vardır. Tercih sayfa açıkken değişirse hemen uygulanır.
- **Logo:** sahne dışında (sekme simgesi, üst çubuk, ürün sayfaları) logo her zaman asıl çizimdir.

### Sahneler

Üç sahnenin çalışan denemeleri `2026-11-26-tasarim-sistemi-ekler/` içindedir. Yapımda bunlar başlangıç noktasıdır ve yeniden kullanılabilir modüllere çevrilir (bkz. Dosya düzeni). Deneme kodu olduğu gibi kopyalanmaz.

**1. Kendini kuran yazı (kimlik anı)** · `sahne-kendini-kuran-yazi.html`

- Açılışta logo kendini kurar: önce kor O, sonra C, en son dalga. Ardından giriş başlığı kendini kurar.
- Harfler Council Halka'nın gerçek glif geometrisinden çizilir: çubuklar uzar, yaylar tam dairelerinden kesilerek çizilir, eğik çubukların kesikleri en sonda yerine oturur.
- Kurulum bitince görüntü yazı tipiyle birebir aynıdır. Toplam süre en fazla 1,8 sn.
- Oturum başına bir kez oynar. Bölüm başlıkları kurulmaz, hazır gelir.
- Ürün sayfalarında amblem aynı sırayla kurulur (Kasa'da anahtar deliği).
- JavaScript çalışmazsa her şey hazır görünür. Gizleme yalnız betik köke bir sınıf eklediğinde devreye girer.
- 0.2 küçük harfleri geldiğinde sahne yeni glifleri de kurabilmelidir.

**2. Çizgi ve söz (sahne)** · `sahne-cizgi-ve-soz.html`

- Logonun iki biçimi vardır:
  - Çizgi: asıl logo.
  - Söz: aynı geometri, harflerle. C, Council Halka ile dizilmiş "BİRÇOK ÜYE · TEK HAFIZA" yazısından; dalga "ORTAK HAFIZA" yazısından kurulur.
- Kor O (hafıza) iki biçimde de hiç değişmez, geçişte bile kesilmez.
- Bölüm görününce logo bir kez 45° kesikli geçişle (840 ms) söze geçer, yaklaşık 6 saniye kalır, çizgiye döner ve durur.
- Bölümde iki Tek Kesik düğmesiyle biçim elle seçilebilir.
- Başlık: "Logo hem çizgidir hem söz."
- Hareket azaltılmışsa ya da betik çalışmıyorsa iki biçim yan yana durur; telefonda alt alta dizilir.
- Altı özelliğin adları belli olunca C'deki yazı bu adlarla değiştirilebilir. Bu yalnız metin değişikliğidir.

**3. Kurul turu (sahne, "Nasıl çalışır" bölümü)** · `sahne-kurul-turu.html`

- Kaydırma, sahnenin zamanıdır. Ziyaretçi kaydırmayı bırakınca sahne de durur. Toplam yükseklik en fazla 450vh. Üstte "Hikâyeyi atla" bağlantısı vardır.
- Altı adım:
  1. **Amblem.**
  2. **Altı özellik:** C altı parçaya (6 × 45°) ayrılır. Parçalar alttaki uçtan saat yönünde dizilir:
     - Hafıza: dolu, "tamam".
     - Kişisel gelişim: yarıya kadar dolu, ucu düz kesik, "denemede".
     - Kalan dört parça: içi boş ince bir çerçeve. Adlarının yerinde kesik çizgiler ve "yolda" etiketi durur.
  3. **Hafıza:** dalga bir notu kor halkaya yazar ("telefon → hafıza · toplantı kararı · yazıldı"), sonra başka bir cihaz okur ("hafıza → bilgisayar · okundu"). Yazma ve okuma C'nin ağzından ("cihazlar") gösterilir.
  4. **Kişisel gelişim:** yardımcı öğrendiğini kaydeder, tek satırla haber verir, istersen geri alınır. Öğrenilen şey bu parçaya taşınır.
  5. **Yolda:** dalga yoldaki dört parçanın üstünden geçer. "Testi ve ölçümü geçen eklenir."
  6. **1.0.0:** etiketler çekilir, altı parça sırayla dolar, amblem yeniden tek bir C olur. Altında "altısı dolduğunda → sürüm 1.0.0" ve "henüz değil" yazar.
- Parçaların bugünkü durumu (hangisi dolu, hangisi denemede, adı ne) tek bir veri listesinden okunur. Yeni bir özellik eklendiğinde yalnız bu liste değişir. README'deki kapak görseli de ileride aynı listeden üretilebilir.
- Hareket azaltılmışsa altı adım altı duran kare olarak gösterilir. JavaScript yoksa duran amblem ve altı açıklama alt alta görünür.
- Kor yalnız ortadaki O'dadır. Taşınan not zemin renginde bir kesiktir.

### Simge seti

- 24 piksellik ızgara, 2 piksel çizgi, düz uçlar, yalnız üç ilke (halka parçası, düz çubuk, eğik çubuk).
- 45° yalnız "dışarı / çıkış / git" anlamında kullanılır.
- İlk aşamada yaklaşık 30 simge çizilir. Listeyi site ve panel ihtiyaçlarına bakarak yapımcı çıkarır: menü, kapat, ara, ayarlar, cihaz türleri, not, geçmiş, bağlantı, indir, kopyala, uyarı vb.
- Her simge tek bir SVG dosyasıdır ve `currentColor` kullanır.

### Amblem ailesi

- C ve kor halka her üründe aynıdır; ortadaki işaret ürünü söyler.
  - Hafıza (COUNCIL): dalga.
  - Kasa: anahtar deliği. 400 birimlik karede daire merkezi (200, 182), yarıçap 34; gövde x=186, y=182, 28 × 76.
- Yeni ürünlerin işaretleri aynı ilkelerle çizilir ve sahibin onayına sunulur.
- Ortadaki işaret tek başına ürünün 24 piksellik simgesi olarak kullanılabilir.
- Sistem amblem çizen bir yardımcı (betik ya da SVG şablonu) içerir. Böylece yeni ürünün amblemi tek bir işaret tanımıyla üretilir.

### Dosya düzeni

Bu düzen Claude'un önerisidir. Yapımcı adları değiştirebilir, ama tek kaynak ilkesini değiştiremez.

```
brand/
  README.md            marka kitabı (Türkçe)
  tokens.json          bütün değerler: renk (iki tema), yazı, boşluk, köşe, hareket — tek kaynak
  build.py             tokens.json'dan CSS değişkenlerini üretir, dosyaları yerleştirir
  css/
    council.css        değişkenler + temel stiller + bütün bileşenler (üretilen kısım işaretli)
  js/
    sahne/             üç sahne modülü (yazi-kur, cizgi-soz, kurul-turu) + ortak yardımcılar
    ozellikler.json    altı parçanın bugünkü durumu
  font/                build_font.py ve çıktılar (0.2)
  logo/                mevcut logo seti (değişmez) + amblem yardımcısı
  simge/               SVG simgeler
  ornek/index.html     canlı örnek sayfası
```

- DM Sans ve DM Mono dosyaları (OFL lisans metinleriyle) `brand/font/` altına kopyalanır. Panel şimdilik kendi kopyalarını ve 0.1 `CouncilHalka.woff2`'yi kullanmaya devam eder; panele bu projede dokunulmaz. Panel testlerinin beklediği dosyalar yerinde kalır.
- **Glif geometrisi tek kaynaktan gelir.** `build_font.py`, yazı tipini üretirken her glifin ilkellerini (çubuk, halka parçası, eğik çubuk; koordinatlarıyla) bir veri dosyasına da yazar (ör. `brand/font/glifler.json`). "Kendini kuran yazı" sahnesi glifleri bu dosyadan çizer; geometri JavaScript'e elle kopyalanmaz. Sahne yalnız kullandığı glifleri yükler, böylece 15 KB bütçesi korunur (Claude'un kararı).
- **Logo:** `build_logo.py` yeni TTF'yi okuyabilir. Büyük harf glifleri değişmediği için logo SVG'leri bayt bayt aynı çıkmalıdır; çıkmazsa yapı durur. Büyük harf çiftleri için eklenen harf aralıkları logoyu etkilemez, çünkü logo kendi harf arasıyla (60 birim) dizilir.
- **claude.ai tasarım sistemi sayfası:** mevcut sayfa (`https://claude.ai/artifact/G8cQpAbyJ8JdzyMNXCWP3P`, özel) claude.ai'nin "Design System" türünden bir sayfadır. İçeriği kendi `project/` dosyalarında durur: `design-system.json` (dizin), `tokens.json`, `README.md`, `components/<Ad>/README.md` ve `preview.html`, `components/bundle.css`, `fonts/`. Sayfa yeni bir bağlantı açılmadan, aynı adresin üstüne koddan yeniden yayınlanır; böylece eski bağlantı çalışmaya devam eder. Dizindeki `"editing": "code"` alanı sayfayı salt okunur yapar ve "koddan eşitlenir" işaretidir. Kodda bir şey değişince sayfa Claude Code'daki tasarım eşitleme komutuyla (`/design-sync`) yeniden üretilir.
- Bu sayfanın `tokens.json` biçimi bir liste biçimidir: her aile `{"tokens": [{"name", "value", "usage"}]}`, renkler iki temalı (`{"light": …, "dark": …}`), yazı ailesi `fonts`, `families` ve `groups` alanlarıyla. Bu biçim 0.1'de zaten kullanıldı. `brand/tokens.json` doğrudan bu biçimde tutulur; böylece aynı dosya hem `build.py`'nin girdisi hem sayfanın içeriği olur.

### Doğrulama

- **Karşıtlık:** bir betik `tokens.json` içindeki her metin ve zemin çiftini iki temada ölçer. Sınırın altında kalan çift yapıyı durdurur.
- **Yazı tipi:** her glif 200 piksel boyda tek tek incelenir. 2026-11-17'de 2 rakamında çıkan boşluk ancak bu boyda görülmüştü. Logo yeniden üretilip eskisiyle karşılaştırılır.
- **Örnek sayfa:** açık tema, koyu tema, 375 piksel ve 1280 piksel genişlikte, hareketi azaltma açık ve kapalı, JavaScript kapalı olarak bakılır. Yatay taşma olmamalı.
- **Sahneler:** boştayken kare çizilmediği ölçülür. Sahne ekran dışındayken dinleyicinin bağlı olmadığı denetlenir. Gerçek kaydırmada akıcılığa yapımcı (Claude) iki yerde bakar: masaüstü Chrome'da ve bu Mac'teki iOS Simülatörü'nde Safari ile. Sahip, onaydan önce örnek sayfayı kendi telefonunda bir kez açıp kaydırır. Firefox'ta yalnız sayfanın bozulmadan açıldığı denetlenir (Claude'un kararı).
- **İçerik taraması:** araç adları ve kişisel bilgi için otomatik bir tarama yapılır; ikisi de 0 çıkmalıdır.
- Mevcut testler (`pytest`) bozulmaz. `brand/` için ayrı ve hafif bir denetim betiği yeterlidir.

## Yapımcıya bırakılanlar

- Küçük harflerin tek tek biçimi, x yüksekliği, harf çifti listesi. Sahibe büyük boyda örnek sayfasıyla gösterilir.
- Simge listesinin kesin içeriği.
- CSS sınıf adları. Türkçe ve kısa olmaları, 0.1'deki `c-` önekinin korunup korunmayacağı.
- `tokens.json` biçiminin ayrıntısı. claude.ai tasarım sistemi sayfasının okuyabildiği liste biçimine uyması gerekir.
- Sahne modüllerinin dışa açtığı arayüz (nasıl çağrıldıkları).

## Claude'un verdiği kararlar (sahip okurken denetlesin)

- Yazı tipleri yerelden yüklenir, Google Fonts kullanılmaz.
- Metin içi bağlantılar kesik almaz.
- Odak çizgisi `kor-metin` renginde kalır. 0.1'de kor zaten "odaktaki öğe" için de tanımlıydı. Sahnelerde odaklanan düğme yoksa tek kor yine O'dur.
- Kişisel gelişim parçası "denemede" durumunu yarım dolulukla gösterir.
- Glif geometrisi `build_font.py`'nin ürettiği veri dosyasından okunur; sahneye elle kopyalanmaz.
- claude.ai tasarım sistemi sayfası aynı adresin üstüne yeniden yayınlanır (yeni bağlantı açılmaz).
- Panel bu projede 0.1 yazı tipi kopyasında kalır.
- Akıcılık denemesi: Claude Chrome ve iOS Simülatörü'nde bakar; sahip kendi telefonunda bir kez bakar.
- Kurul turunun sonunda altı parçanın dolması bir gelecek önizlemesidir ve "henüz değil" yazısıyla verilir.
- 0.1'deki 6 ve 12 piksellik köşeler kaldırılır.
- Dosya düzeni (yukarıda).
