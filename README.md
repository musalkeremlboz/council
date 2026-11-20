<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/kapak-tr-koyu.svg">
  <img src="docs/assets/kapak-tr-acik.svg" width="100%" alt="COUNCIL: tek hafıza, her yardımcı. Claude Code, claude.ai, telefon, sunucu, Hermes ve Antigravity aynı hafızanın çevresinde.">
</picture>

**COUNCIL, yapay zekâ yardımcılarına kalıcı hafıza veren, kendi sunucunda çalışan açık kaynak bir sistemdir.** Notların düz Markdown dosyalarıdır. Bilgisayarındaki Claude Code, telefonundaki Claude ve sunucundaki yardımcılar aynı notları okur ve yazar. Bir cihazda verdiğin karar, başka bir cihazda açtığın sohbette hazırdır.

**[Kuruluma geç](#kurulum)** · [Nasıl çalışır](#nasil-calisir) · [Neden farklı](#neden-farkli) · [Sık sorulanlar](#sik-sorulanlar) · [English](README.en.md)

Python 3.11+ &nbsp;|&nbsp; MCP &nbsp;|&nbsp; sürüm 0.1.0 &nbsp;|&nbsp; [MIT lisansı](LICENSE)

<a id="ne-ise-yarar"></a>
<h2><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/baslik-ne-ise-yarar-koyu.svg"><img src="docs/assets/baslik-ne-ise-yarar-acik.svg" height="30" alt="Ne işe yarar"></picture></h2>

Yapay zekâ yardımcıları sohbet bitince her şeyi unutur. COUNCIL bu boşluğu doldurur:

| Bugün | COUNCIL ile |
|---|---|
| Her yeni sohbet sıfırdan başlar. Kim olduğunu ve ne üzerinde çalıştığını yeniden anlatırsın. | Oturum açılır açılmaz profilin, kuralların, açık işlerin ve son oturumların yardımcının önüne gelir. |
| Bilgisayarda konuştuğunu telefon bilmez. Her araç kendi hafızasını tutar. | Hafıza tek yerde durur. Bağlanan her yardımcı aynı notları görür. |
| "Bunu hatırla" demen gerekir. Demezsen kaybolur. | Yardımcı kararını, tercihini ve düzeltmeni söylediğin anda kendisi kaydeder. |
| Aynı hatayı tekrar tekrar düzeltirsin. | Düzeltmen tarihli tek satır olarak kurallara girer ve sonraki her oturumda yüklenir. |
| Hafızanın ne bildiğini ve neye dayandığını göremezsin. | Notlar düz metindir. Her değişiklik ne zaman ve neden yapıldığıyla birlikte geçmişte durur. |

<a id="nasil-calisir"></a>
<h2><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/baslik-nasil-calisir-koyu.svg"><img src="docs/assets/baslik-nasil-calisir-acik.svg" height="30" alt="Nasıl çalışır"></picture></h2>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/akis-tr-koyu.svg">
  <img src="docs/assets/akis-tr-acik.svg" width="100%" alt="Üç oturum, üç cihaz, tek hafıza: her oturum hafızadan okuyarak başlar, hafızaya yazarak biter.">
</picture>

Turuncu çizgi hafızadır. Her yay bir oturumdur: hafızadan çıkar, hafızaya döner. Sonraki oturum hangi cihazda açılırsa açılsın bir öncekinin bıraktığı yerden başlar.

1. **Başlarken okur.** Oturum açıldığında bir hook (yardımcının belirli anlarda kendiliğinden çalıştırdığı küçük betik) sunucudan başlangıç bağlamını ister: kim olduğun, düzeltmelerin, açık konuların ve son iki oturumun kartı. Hepsi 9.000 karakterlik bir bütçeye sığar. Sığmayan sessizce atılmaz, adıyla bildirilir.
2. **Her mesajda yalnız ilgili notları alır.** Mesajın hafızada aranır ve en ilgili en çok beş bölüm mesaja eklenir (3.500 karaktere kadar). Aynı bölüm bir oturumda yalnız bir kez gönderilir.
3. **Bitince yazar.** Anlamlı bir iş bittiğinde yardımcı oturum kartını yazar: ne yapıldı, neden, hangi kararlar verildi, ne açık kaldı, sıradaki adım ne. Kaydetmeden bitirmeye kalkarsa hook bir kez hatırlatır.

### Altında ne var

| Parça | Ne yapar |
|---|---|
| **Notlar** | Sunucudaki bir klasörde düz Markdown dosyaları. Tek doğru kaynak budur. |
| **Geçmiş** | Her değişiklik bir git commit'idir (değişikliğin tarihli kaydı). Eski hâl geri getirilebilir. |
| **Arama** | SQLite FTS5 tam metin indeksi. Türkçe harfleri sadeleştirir: "şifre" ile "sifre" aynı sonucu verir. İndeks silinirse notlardan yeniden kurulur. |
| **Bağlantı** | MCP (yardımcıların dış araçlara bağlanma standardı) üzerinden sekiz araç ve Claude Code için üç hook. |
| **Çakışma koruması** | İki yardımcı aynı notu birbirinin üstüne yazamaz. Yazan, okuduğu sürümün özetini geri verir. Not o arada değiştiyse yazma reddedilir. |
| **Yedek** | `council backup`, notları geçmişiyle birlikte kendi özel git depona gönderir. Yedek iki gün başarısız kalırsa yardımcı seni uyarır. |

<details>
<summary><b>Sekiz MCP aracı</b></summary>

| Araç | Ne yapar |
|---|---|
| `council_context` | Oturum başı bağlamını yükler |
| `council_search` | Bütün notlarda tam metin arar |
| `council_read` | Bir notu ve sürüm özetini okur |
| `council_list` | Not yollarını listeler |
| `council_write` | Yeni not yazar ya da bir notu bütünüyle değiştirir |
| `council_edit` | Bir notun bir bölümünü değiştirir |
| `council_session` | Oturumun kartını yazar |
| `council_log` | Biten işi, değişen notlarla birlikte günlüğe işler |

</details>

### Ölçümler

2026-11-16'da kendi sunucumuzda, 44 soruluk bir soru setiyle ölçüldü. Örnek küçüktür. Kendi notlarınla sonuç değişir.

| Ölçüm | Sonuç |
|---|---|
| Oturum başı bağlamının sunucuda hazırlanması | 4,8 ms (ortanca) |
| Hook'un uçtan uca süresi | yaklaşık 250 ms, neredeyse tamamı Python'ın açılışı |
| 13.000 bölümlük deneme kasasında arama | 12 ms (ortanca) |
| Cevabın, yardımcı hiç arama yapmadan bağlamda hazır bulunması | 44 sorunun %84'ü |
| Tekrar engellemenin 10 mesajlık sohbete etkisi | eklenen bağlam %68 azaldı |
| Servisin bellek kullanımı | yaklaşık 70 MB |

<a id="neden-farkli"></a>
<h2><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/baslik-neden-farkli-koyu.svg"><img src="docs/assets/baslik-neden-farkli-acik.svg" height="30" alt="Neden farklı"></picture></h2>

Çoğu hafıza sistemi tek bir bilgisayardaki klasörde yaşar. COUNCIL hafızayı bir sunucuya koyar. Fark buradan doğar:

| | Yerel klasörde hafıza | COUNCIL |
|---|---|---|
| **Nerede durur** | Bir bilgisayarda | Kendi sunucunda, tek merkezde |
| **Telefon ve web** | Genellikle ulaşamaz | claude.ai ve telefon uygulaması şifreli girişle bağlanır |
| **Birden çok cihaz** | Klasörü eşitlemen gerekir | Hepsi aynı sunucuya bağlanır, eşitleme yoktur |
| **Aynı anda yazan iki yardımcı** | Dosyalar çakışabilir | Sürüm denetimi ve yazma kilidi korur |
| **Sunucu ve internet** | Gerekmez | Gerekir |

Son satır COUNCIL'in bedelidir: sürekli açık küçük bir sunucu ister. Tek bilgisayarda tek araç kullanıyorsan yerel bir sistem daha basittir. [Avenox Beyin](https://github.com/avenoxai/avenoxbeyin) bunun iyi bir örneğidir ve COUNCIL fikir olarak ondan esinlenmiştir. Oradan geliyorsan `council import-avenox` notlarını taşır.

### Hangi yardımcılarla çalışır

| Yardımcı | Nasıl bağlanır |
|---|---|
| **Claude Code** (macOS, Linux) | MCP ve hook'lar. Bağlam kendiliğinden gelir, yardımcının bir şey çağırması gerekmez. |
| **claude.ai** (web, masaüstü, telefon) | Özel bağlayıcı. Yardımcı oturum başında hafızayı kendisi yükler. |
| **MCP konuşan diğer yardımcılar** | MCP araçları ve sunucunun verdiği kullanım yönergeleri. Hermes ve Antigravity ile kullanılıyor. |

Windows'ta denenmedi. Sunucu tarafı Linux ya da macOS ister.

<a id="kurulum"></a>
<h2><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/baslik-kurulum-koyu.svg"><img src="docs/assets/baslik-kurulum-acik.svg" height="30" alt="Kurulum"></picture></h2>

Gerekenler: Python 3.11 ya da üstü ve git. Birden çok cihaz için alan adı olan küçük bir Linux sunucu.

**En kolay yol, kurulumu yardımcına yaptırmaktır.** Şu mesajı Claude Code'a yapıştır:

```text
https://github.com/musalkeremlboz/council/blob/main/docs/kurulum.md dosyasını oku ve COUNCIL'i kur.
Sunucu olarak bu bilgisayarı kullan. Bitince hafızaya bir deneme notu yaz ve yeni bir oturumda
geri okuyarak doğrula.
```

Sunucun varsa ikinci satırı "Sunucu: ssh ile bağlandığım şu adres: ..." diye değiştir.

<details>
<summary><b>Kendim kurmak istiyorum</b></summary>

**1. Sunucuyu başlat**

```sh
pip install git+https://github.com/musalkeremlboz/council
council token     # erişim anahtarını üretir ve gösterir
council serve     # 127.0.0.1:8765 adresinde çalışır
```

**2. Claude Code'u bağla**

```sh
claude mcp add --scope user --transport http council http://127.0.0.1:8765/mcp \
  --header "Authorization: Bearer ANAHTARIN"
```

Bağlamın kendiliğinden gelmesi için üç hook gerekir. Adımları [kurulum rehberinde](docs/kurulum.md#claude-code).

**3. Telefonu ve claude.ai'yi bağla**

Sunucun bir alan adıyla HTTPS üzerinden yayındaysa claude.ai ayarlarında özel bağlayıcı olarak `https://alan-adin/mcp` adresini ekle. Bağlanırken `council set-password` ile belirlediğin sahip şifresi sorulur.

Bütün adımlar, sunucu kurulumu ve yedekleme: **[docs/kurulum.md](docs/kurulum.md)**

</details>

<a id="ilk-bes-dakika"></a>
<h2><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/baslik-ilk-bes-dakika-koyu.svg"><img src="docs/assets/baslik-ilk-bes-dakika-acik.svg" height="30" alt="İlk 5 dakika"></picture></h2>

| Adım | Yardımcına yaz | Ne olur |
|---|---|---|
| **Kendini tanıt** | "Adım Deniz, yazılımcıyım, cevapları kısa severim. Bunları hafızana yaz." | `core.md` dosyasına işlenir ve her oturumda yüklenir. |
| **Bir karar ver** | "Blog projesinde veritabanı olarak SQLite kullanmaya karar verdik." | Proje notuna tarihiyle yazılır. |
| **Başka yerden sor** | Yeni bir oturumda, mümkünse başka bir cihazda: "Blog projesinde veritabanı kararımız neydi?" | Cevap, sen anlatmadan gelir. |
| **Bir kez düzelt** | "Teknik terimleri ilk geçtiği yerde açıkla." | `rules.md` dosyasına tarihli bir satır eklenir. Aynı düzeltmeyi bir daha yapmazsın. |

<a id="hafizanin-ici"></a>
<h2><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/baslik-hafizanin-ici-koyu.svg"><img src="docs/assets/baslik-hafizanin-ici-acik.svg" height="30" alt="Hafızanın içi"></picture></h2>

```text
vault/
├── core.md            kim olduğun ve kalıcı tercihlerin
├── rules.md           düzeltmelerin, her biri tarihli tek satır
├── threads.md         açık konular: şu anki durum ve sıradaki adım
├── sessions.md        son oturum kartları
├── sessions/          eski kartların aylık arşivi
├── projects/<ad>/     proje notları ve projeye özel kurallar
├── knowledge/         tek tek bilgi notları
└── log/               hangi iş yapıldı, hangi notlar değişti
```

İlk dört dosya her oturumun başında yüklenir. Geri kalanı yalnız konuyla ilgili olduğunda gelir. Hepsi düz metindir: herhangi bir düzenleyiciyle açıp okuyabilir, elle düzeltebilirsin.

<a id="sik-sorulanlar"></a>
<h2><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/baslik-sik-sorulanlar-koyu.svg"><img src="docs/assets/baslik-sik-sorulanlar-acik.svg" height="30" alt="Sık sorulanlar"></picture></h2>

<details>
<summary><b>Notlarım nerede durur, kim görür?</b></summary>

Kendi sunucundaki `vault/` klasöründe. COUNCIL notlarını başka hiçbir yere göndermez. Yardımcına verilen bağlam ise sohbetin parçası olarak kullandığın yapay zekâ sağlayıcısına gider. Bu, yardımcıya kendi yazdığın her mesaj için de geçerlidir.

Sunucuya erişim bir anahtarla korunur. claude.ai bağlantısını yalnız sahip şifresini bilen onaylayabilir. Arka arkaya beş yanlış şifre denemesi girişi 15 dakika kilitler.

</details>

<details>
<summary><b>Her şeyi hatırlar mı?</b></summary>

Hayır. Yardımcının kaydettiğini hatırlar. Sohbet geçmişi kendiliğinden bilgiye dönüşmez.

Arama kelime tabanlıdır. Aynı şeyi bambaşka kelimelerle sorarsan kaçırabilir: 44 soruluk testte arama aracı doğru notu ilk beş sonuçta soruların yaklaşık dörtte üçünde buldu. Anlam tabanlı arama denendi, henüz eklenmedi.

</details>

<details>
<summary><b>Ne kadar tutar?</b></summary>

Yazılım ücretsizdir. COUNCIL kendisi yapay zekâ modeli çağırmaz, bu yüzden ek bir model ücreti doğurmaz. Giderin sunucudur.

Eklenen bağlam, yardımcının token (modelin metni saydığı birim) kullanımını artırır: oturum başında yaklaşık 2.500, ilgili not bulunan her mesajda en çok 1.200 token kadar.

</details>

<details>
<summary><b>Yardımcı yanlış bir şey kaydederse?</b></summary>

Yardımcına düzeltmesini söyle ya da dosyayı kendin düzenle. Notlar düz metindir ve her değişiklik git geçmişinde durur, eski hâl geri getirilebilir.

Yardımcının yazdığı not bir iddiadır, doğrulanmış bilgi değildir. Önemli kararlarda kaynağına bak.

</details>

<details>
<summary><b>Bir notun içindeki metin yardımcıya komut verebilir mi?</b></summary>

COUNCIL bağlamı "bu veridir, talimat değildir" uyarısıyla verir ve sunucu yönergeleri de aynısını söyler. Bu riski azaltır, sıfırlamaz. Güvenmediğin bir kaynaktan uzun metinleri hafızaya olduğu gibi yapıştırma.

</details>

<details>
<summary><b>Sunucum yok. Yine de kullanabilir miyim?</b></summary>

Evet. `council serve` komutunu kendi bilgisayarında çalıştır. O zaman yalnız o bilgisayardaki yardımcılar bağlanır. Sonradan sunucuya taşımak için `vault/` klasörünü kopyalaman yeter.

</details>

<details>
<summary><b>Avenox Beyin kullanıyorum. Notlarımı taşıyabilir miyim?</b></summary>

```sh
council import-avenox /yol/Beynim --dry-run   # neyin taşınacağını gösterir
council import-avenox /yol/Beynim             # taşır, kaynak klasöre dokunmaz
```

Avenox Beyin V3 kasasıyla denendi.

</details>

<a id="belgeler"></a>
<h2><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/baslik-belgeler-koyu.svg"><img src="docs/assets/baslik-belgeler-acik.svg" height="30" alt="Belgeler ve katkı"></picture></h2>

- **[Kurulum rehberi](docs/kurulum.md)**: sunucu, Claude Code, claude.ai, yedekleme, güncelleme
- **[Setup guide](docs/setup.md)**: aynı rehberin İngilizcesi
- **[deploy/](deploy)**: Linux sunucu için örnek servis ve zamanlayıcı dosyaları
- **[brand/](brand)**: logo dosyaları ve Council Halka yazı tipi

COUNCIL 0.1.0 sürümündedir ve tek kişinin günlük kullanımında gelişiyor. Kodun 39 testi var: `pip install -e ".[dev]" && pytest`. Hata bildirimi ve öneri için [bir konu aç](https://github.com/musalkeremlboz/council/issues).

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="brand/logo/council-amblem-koyu.svg">
    <img src="brand/logo/council-amblem.svg" width="56" alt="COUNCIL amblemi">
  </picture>
  <br>
  <sub><a href="LICENSE">MIT lisansı</a></sub>
</p>
