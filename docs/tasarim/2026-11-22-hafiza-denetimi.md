# Hafıza denetimi: arama soruları, bulunamayan terimler, kırık bağlantılar

**Durum:** onay bekliyor (2026-11-22). Kod yazılmadı.
**Kaynak:** proje sahibinin isteği (2026-11-22 00:28, 00:38). Üç fikir başka bir hafıza aracının sürüm notlarından esinlendi; kod alınmaz.

## Neden

Hafıza büyüdükçe iki şey sessizce bozulur: bir soru doğru notu getirmez olur, bir not taşınınca ona giden bağlantılar boşa düşer. Bugün ikisini de ancak bir yardımcı işin ortasında fark ederse görüyoruz. Bu belge, ikisini istendiğinde ölçen tek bir komut ve aramaya küçük bir ek tanımlar.

## Hedef, hedef dışı

- **Hedef:** hafızanın doğru notu bulup bulmadığını sahibinin kendi sorularıyla ölçmek; kırık bağlantıları listelemek; açık aramada hafızada hiç geçmeyen terimleri söylemek.
- **Hedef dışı:** aramanın kendisini değiştirmek (sıralama, anlamsal arama). Bu belge ölçüm aracını getirir; aramayı değiştirecek her öneri sonra bu araçla sınanır.
- **Hedef dışı:** kırık bağlantıyı kendiliğinden düzeltmek. Komut yalnız bildirir.
- **Olmaması gereken:** her mesajın bağlamına yeni satır eklemek (aşağıda ölçüldü, gürültü).

## 1. Arama soruları

**Ne:** `council check` komutu, kayıtlı her soru için hafızanın beklenen notu getirip getirmediğine bakar.

- **Soru kaydı:** `<veri klasörü>/questions.json`; her kayıt bir soru, beklenen bir ya da birkaç not yolu ve eklenme tarihi. Ekleme: `council check add "soru" yol/not.md`. Çıkarma: `council check remove "soru"`.
- **Ölçülen iki yol:** (a) mesajda kendiliğinden gelen ilgili notlar (bugünkü kural: en çok 5 bölüm), (b) açık arama (en çok 8 sonuç). Beklenen notun herhangi bir bölümü gelmişse isabettir.
- **Çıktı:** iki yol için ayrı ayrı `x/N`; kaçan her soru için beklenen not ve onun yerine gelen ilk üç not. Beklenen not artık yoksa kaçmış sayılmaz, "not yok" diye ayrı listelenir.
- **Sorular nereden gelir:** sahibi "şunu bulman gerekirdi" dediğinde ya da yardımcı, kendiliğinden gelmesi gereken bir notu elle aramak zorunda kaldığında ekler. İlk küme için kullanım kaydındaki gerçek mesajlardan aday çıkarılır ve sahibine tek listede gösterilir.

**Yaklaşımlar:**

| Soru kaydı nerede durur | Artı | Eksi |
|---|---|---|
| Veri klasöründe dosya **(seçilen)** | Aramaya karışmaz; sunucunun yerel yedeğine girer | Notların git geçmişinde yok |
| Hafızada bir not | Yedeklenir, her yardımcı yazabilir | Sorular aramada kendileriyle eşleşir, ölçümü bozar |
| Kullanım kaydından otomatik | Emek istemez | Beklenen not bilinmez; ölçüm olmaz |

## 2. Açık aramada bulunamayan terimler

**Ölçüm (sahibinin sunucusu, 2026-11-22, yalnız okuma):** hafızada hiç geçmeyen en az bir terim, kendiliğinden bağlam eklenen 276 mesajın 133'ünde (%48) var ve çoğu anlamsız (kimlik parçaları, dolgu sözcükler). Açık aramalarda 20 sorgunun 1'inde (%5).

**Karar:** yalnız açık aramada. Arama aracı ve sorgulu bağlam aracı, sorgudaki terimlerden hafızanın hiçbir notunda geçmeyenleri ayrıca bildirir (en çok 8 terim). Mesaj başına eklenen bağlama dokunulmaz.

- Arama aracının yanıtı `{"hits": [...], "not_found": [...]}` olur (bugün yalnız liste). Bu, aracı kullanan betikler için biçim değişikliğidir.
- Beklenen yarar küçük: yirmi aramada bir tetiklenir. Tetiklendiğinde yardımcıya "bu konuda hafızada hiçbir şey yok" bilgisini verir; yardımcı var saymaz, sorar ya da başka yere bakar.

## 3. Kırık bağlantılar

**Ölçüm (aynı sunucu):** notlarda 320 `[[...]]` bağlantısı var, 20'si var olmayan nota gidiyor (hepsi adı değişen bir proje klasörüne). Ters tırnak içindeki 138 dosya yolunun 59'u hafızanın dışındaki dosyaları gösteriyor; bunlar bağlantı değil.

**Ne:** `council check` aynı çalışmada bağlantıları da denetler.

- **Denetlenen:** `[[hedef]]` ve `[metin](hedef.md)`. Hedef, hafıza köküne ve notun klasörüne göre, `.md` ekli ve eksiz denenir.
- **Denetlenmeyen:** ters tırnak içindeki yollar; web adresleri; `log/` ve `sessions/` (geçmiş kayıtları, yazıldıkları günün hâlini gösterir).
- **Çıktı:** not → kırık hedef. Aynı dosya adı başka bir klasörde varsa "olası yeni yer" olarak yanına yazılır.

## Komutun biçimi

`council check` ikisini birlikte çalıştırır; `council check search` ve `council check links` ayrı ayrı. Hiçbiri hafızayı değiştirmez. Kaçan soru ya da kırık bağlantı varsa çıkış kodu 1'dir (zamanlanmış görevlerde kullanılabilsin diye).

## Doğrulama

- Depoda testler: soru ekleme, çıkarma, isabet ve kaçma sayımı, "not yok" durumu; bağlantı biçimlerinin her biri, göreli yol, dışarıda bırakılan klasörler, olası yeni yer; aramada bulunamayan terimler ve yanıt biçimi.
- Sahibinin hafızasında: bağlantı denetimi yukarıdaki 20 kırık bağlantıyı bulmalıdır. Arama ölçümünün ilk sonucu bir sınır değil, başlangıç sayısıdır.

## Benim verdiğim kararlar

- Tek komut (`council check`), üç ayrı komut yerine.
- Sorular veri klasöründe, hafızada değil.
- Bulunamayan terimler yalnız açık aramada; ölçüm, mesaj başına eklemenin gürültü olduğunu gösterdi.
- Yeni MCP aracı eklenmez; soru ekleme komut satırından yapılır.
- Zamanlanmış denetim ve otomatik düzeltme bu sürümde yok.

## Yayın

Ayrı dalda yazılır. Ana dala birleştirme ve sahibinin sunucusuna kurma ayrı onayla. Canlı deneme sürerken sunucuya kurulursa: 1 ve 3 yalnız okuyan komutlardır, denemenin ölçütlerini etkilemez; 2 arama aracının yanıtını değiştirir.
