# Skill dizini ve işaret (kişisel gelişim, ek tasarım)

**Durum:** yapıldı (dal `skill-dizini`), ölçüm bekliyor.
**Ana tasarım:** `2026-11-21-kisisel-gelisim.md`. Bu belge onun "Bağlama gelmesi", "İnceleme sorusu" ve "Ölçüm" bölümlerini değiştirir. Ayrıca şu cümleleri geçersiz kılar (ana belgede işaretlendi): "Kapsam dışı" altındaki dizin maddesi, "Nasıl işler" akışındaki "skill bağlama eklenir" ve "gelen skill'ler için bildirir" satırları, "bağlama gelmediği sürece yer tutmaz" cümlesi. Gerisi aynen geçerlidir.
**Hedef sürüm:** 0.3.0.

## Neden

Ana tasarımda skill, mesajla kelime eşleşmesi tutunca bütün metniyle bağlama ekleniyordu. Proje sahibinin 201 gerçek mesajıyla yapılan ölçüm iki şey gösterdi:

- Kelimeler mesajın konusunu gösterir, ne istendiğini göstermez. Kural düzeltildikten sonra bile doğru skill isteklerin %72'sinde geliyor (sınır %80) ve skill'in konusundan söz edip başka bir şey isteyen mesajlara da skill gidiyor.
- İşi yalnız oturumun öncesinden anlaşılan mesajlarda ("evet, yap", "bunu da yükle") kelime eşleşmesi neredeyse hiç tutmuyor (44'te 2).

İsteği ve oturumun öncesini okuyabilen taraf yardımcının kendisidir. Bu ek, seçimi ona bırakır.

## Proje sahibinin kararları

- 2026-11-21 11:35 · "Evet, tasarla": oturum başında skill dizini tasarlansın.
- 2026-11-21 18:45 · "Dizin + işaret": üç yaklaşımdan bu seçildi.

## Hedefler

- Yardımcı, yapılan iş bir skill'in işiyse o skill'i kendisi açar; mesajın sözcükleri skill'in sözcükleriyle tutmasa da.
- Yanlış bir önerinin bedeli tek satırdır.
- Oturum başına eklenen yük küçük ve öngörülebilirdir.
- Hook'u olmayan yardımcılarda da çalışır. (Hook: yardımcının oturum başında ve her mesajda kendiliğinden çalıştırdığı küçük program; hafıza bağlamını o getirir.)

## Kapsam dışı

- Anlamsal arama (kelime yerine anlam benzerliğiyle eşleştirme). Ayrı bir karardır.
- Dizini oturumun projesine göre süzmek. Sunucu oturumun hangi projede olduğunu bilmiyor; bütün canlı skill'ler listelenir.
- Skill'leri yardımcının kendi skill klasörüne aktarmak.

## Olmaması gerekenler

- Bir skill'in metni, yardımcı açmadan bağlama girmez.
- Dizin, oturum başındaki öteki bölümlerin (çekirdek, kurallar, konular, oturum kartları) bütçesinden yemez.
- Dizindeki bir hata oturum başı bağlamının gelmesini engellemez; hata kayda geçer, o oturum dizinsiz başlar.
- Emekli ya da denetimden geçmemiş not dizine ve işarete girmez.
- Açılmamış bir skill için geri bildirim istenmez; yalnız gösterilmiş olmak bir skill'i ne kalıcı yapar ne emekli eder.
- Dizine serbest metin girmez (aşağıda "Dizin"): her oturuma yüklenen bir yere, bir yardımcının yazdığı cümleler konmaz.

## Yaklaşımlar

1. **Dizin + tek satırlık işaret (seçilen).** Oturum başında dizin; mesajda kelime eşleşmesi tutarsa skill'in metni değil, tek satırlık işaret.
2. **Yalnız dizin.** En sade ve yanlış öneri yok; ama uzun oturumda dizin geride kalır ve dizine sığmayan skill'ler hiç gündeme gelmez.
3. **Dizin + bugünkü tam metin.** En çok yakalayan; ama her yanlış eşleşmede 1.500 karakterlik ilgisiz metin bağlama girmeye devam eder.

Seçimin dayanağı aynı 201 mesajda yapılan iki denemedir. Ayrı bir yardımcıya yalnız dizin verildi; skill'lerin içini görmedi ve her mesaj için hangisini açacağını söyledi.

| | Kelime eşleşmesi | Dizin: ad + "ne zaman" (6.800 karakter) | Dizin: yalnız ad (2.330 karakter) |
|---|---|---|---|
| İstek mesajdan anlaşılıyor, doğru skill | %72 (18/25) | %68 (17/25) | %64 (16/25) |
| İstek yalnız oturumun öncesinden anlaşılıyor | %5 (2/44) | %36 (16/44) | %41 (18/44) |
| Hiçbir skill uymuyor, yine de skill | %14 (18/132) | %0 (0/132) | %1 (1/132) |

Kelime eşleşmesi ile ad + "ne zaman" dizininden en az biri isteklerin %92'sinde (23/25) doğru skill'i buluyor: ikisi birbirinin kaçırdığını tamamlıyor. Bu bir üst sınırdır; işaret adayı gösterir, açıp açmamaya yine yardımcı karar verir.

Bu sayılar görülmüş bir kümeden ve tek birer denemeden gelir; yön gösterir, ölçüt sayısı değildir.

## Nasıl işler

### Dizin

- **Ne zaman:** her oturum başında (yeni, sürdürülen ya da sıkıştırılmış oturum), öteki bölümlerden sonra, kendi başlığı altında.
- **İçinde ne var:** canlı her skill için bir satır, yalnız notun yolu. Sunucunun yazdığı skill'lerde yol, skill adının ilk 60 karakterinin küçük harfli ve tireli hâlidir (`skills/docker-port-cakismasini-cozme.md`), yani adı da açma anahtarını da taşır. "Ne zaman" satırı dizine girmez: yalnız yolların verildiği deneme (yukarıdaki son sütun; gerçek, 60 karakterde kesilmiş yollarla yapıldı) adın tek başına yettiğini ve yükün üçte bire indiğini gösterdi.
- **Dizine yalnız kalıba uyan yol girer:** dosya adı yalnız küçük harf, rakam ve tireden oluşan skill'ler. Elle yazılmış, adı bu kalıba uymayan bir skill notu dizine girmez; işaretle yine gelebilir. Böylece dizinde serbest metin olmaz.
- **Başlık:** tek cümle: bunların kayıtlı iş tarifleri olduğunu, istenen iş bunlardan birinin işiyse notun okunup izleneceğini, yalnız konusu geçti diye açılmayacağını söyler.
- **Bütçe:** 3.000 karakter, öteki bölümlerin bütçesinden ayrı; başlık ve "sığmayanlar" satırı bu 3.000'in içindedir. Bugünkü 34 skill 2.330 karakter tutuyor (oturum başına kabaca 700 token). Proje skill'lerinin yolu daha uzundur (`projects/<proje>/skills/...`); bir satır hiçbir zaman kesilmez, sığmıyorsa o skill sığmayanlara sayılır.
- **Sıra ve sığmayanlar:** kalıcı skill'ler önce, sonra adaylar. Her grupta nottaki değişiklik tarihi (yoksa yazılma tarihi) yeni olan önce, eşitlikte yola göre; adaydan kalıcıya geçmek tarihi değiştirmez. Sığmayanlar yalnız sayılır ("… 12 tane daha listelenmedi"); onlar işaretle gündeme gelir.
- **Hook'u olmayan yardımcılar:** oturum başında çağırdıkları bağlam aracı aynı dizini döndürür; araca verdikleri ilk mesaj bir skill'le eşleşiyorsa işaret satırı da eklenir (bugün aynı yerde skill'in tam metni dönüyor). Bu yardımcılar sonraki mesajlarda işaret almaz.

### İşaret

- Her mesajda kelime eşleşmesi bugünkü kuralla çalışır (ana tasarımdaki "Eşleştirme kuralı", 2026-11-21 düzeltmesiyle).
- Eşleşen skill'in metni yerine tek satır eklenir: notun yolu ve "ne zaman" satırı (200 karakterde kesilir, satır sonları boşluğa çevrilir). En çok iki skill; aynı skill bir oturumda bir kez (oturum sıkıştırılınca yeniden gönderilebilir).
- Başlığı, bunun bir öneri olduğunu ve istenen işe uyuyorsa notun okunacağını söyler.
- Ana tasarımdaki 1.500 karakterlik skill bütçesi kalkar.

### Açma ve geri bildirim

- **Açma:** yardımcı skill notunu, öteki notları okuduğu araçla okur. Yeni araç yok.
- **Sayım:** sunucu, canlı bir skill notunun okuma aracıyla okunduğunu kullanım kaydına işler. Arama sonucunda görünmek, emekli bir skill'i ya da skill klasöründeki sıradan bir notu okumak açma sayılmaz.
- **İnceleme sorusu:** bugün "bu oturumda bağlama eklenen skill'ler" için geri bildirim istiyor. Artık yalnız **bir önceki inceleme sorusundan beri o oturumda açılan** canlı skill'ler için ister; aynı skill, yeniden açılmadıkça ikinci kez sorulmaz. Hook, oturumun dökümünden okunan not yollarını sunucuya bildirir; hangilerinin canlı skill olduğuna sunucu karar verir. Değiştirmek için okunan skill de açılmış sayılır.
- Ana tasarımdaki "gösterildi" kaydı kalkar; kalıcılık ve emeklilik kuralları aynen kalır (ikisi de geri bildirime bağlıdır).
- **Yönerge:** sunucunun kullanım yönergesindeki ve geri bildirim aracının açıklamasındaki "gösterilen skill" cümleleri değiştirilir: dizindeki bir skill istenen işin tarifiyse aç ve izle; açtığın skill'in işe yarayıp yaramadığını, yolunu vererek bildir.
- **Skill yazma yönergesi:** "ad, işin kendisini adlandırsın ve en önemli sözcükler başta olsun" cümlesi eklenir; dizin adın ilk 60 karakteriyle çalıştığı için ad artık seçimin dayanağıdır.
- **Adı düzeltmek bu sürümde yok.** Yol addan türediği için yeni adla yazılan skill yeni bir adaydır; eskisi dizinde kalır ve ancak geri bildirimle emekli olur. Bilinen bir sınırdır.

### Kullanım özeti

`council usage` çıktısındaki öğrenme satırlarına iki sayı eklenir: gönderilen işaret (işaret başına sayılır; bir mesajda iki işaret iki sayılır) ve açılan skill (yukarıdaki "Sayım" tanımıyla, bütün yardımcılardan). İkisi yan yana verilir; okuma kaydında oturum bilgisi olmadığı için "şu işaret şu açmayla sonuçlandı" eşlemesi yapılmaz. İşaret, not bazlı "bağlama eklendi" dökümüne sayılmaz.

## Ölçüm

Ana tasarımdaki 1. ölçütün sınırları aynen kalır (konulu en az %80, konu dışı en çok %20); ölçme biçimi değişir, çünkü seçimi artık kod değil yardımcı yapıyor.

1. **Uçtan uca seçim (ölçütün sayısı).** Proje sahibinin bu belgenin tarihinden sonraki gerçek mesajlarıyla, bir kez. Eşleştirme kodunu ve etiketleri görmeyen bir yardımcıya, sunucunun o oturumda vereceği dizin ve işaretler verilir; mesajları oturum sırasıyla okur ve her mesajda hangi skill'i açacağını söyler. Etiketleri başka bir yardımcı, skill'lerin tamamını görerek yazar. Kural ölçümden önce yazılır.
   - Konulu: işi mesajın kendisinden anlaşılan isteklerde doğru skill'in açılma oranı, en az %80.
   - Konu dışı: hiçbir skill'in uymadığı mesajlarda bir skill'in açılma oranı, en çok %20.
   - İşi yalnız oturumun öncesinden anlaşılan istekler ayrıca bildirilir, ölçüte girmez.
   - En az 25 konulu mesaj birikmeden ölçülmez.
   - **Skill kümesi:** ölçüm günü, proje sahibinin notlarından (`projects/council/` dışında) eşleştirme kodunu ve mesajları görmeyen bir yazarın yazdığı skill'ler; etiketlemeden önce sabitlenir. Proje sahibinin kurulumunda o güne dek gerçekten yazılmış skill'ler varsa kümeye eklenir.
   - **Seçim:** yardımcı her mesaj için en çok iki skill söyleyebilir; beklenen skill bunların arasındaysa isabettir. Aynı oturumda daha önce açtığı skill'i, iş yine onun işiyse yeniden söyler (her mesaj ayrı sayılır). İşaretler sunucunun vereceği gibi verilir: skill başına oturumda bir kez.
   - **Model:** proje sahibinin günlük kullandığı yardımcının modeli, varsayılan ayarla, tek koşu; sonuçla birlikte modelin adı yazılır.
2. **Depodaki testler (her değişiklikte).** İki senaryo kümesi işaretin kalitesini ölçmeye devam eder. Dizin için: biçim, bütçe, sıra, sığmayanların sayılması, emekli ve denetimsiz notun girmemesi, hata hâlinde bağlamın yine gelmesi.
3. **Canlı deneme (iki hafta, ana tasarımdaki 2. ve 3. ölçüt aynen).** Ek olarak bildirilir: kaç işaret gönderildi, kaç skill açıldı, kaç geri bildirim "işe yaradı" dedi. Bunlar ölçüt değildir; yardımcının gerçek iş sırasında dizine bakıp bakmadığını gösteren tek veridir.

## Sınırlar

- Denemelerde yardımcı yalnız seçim yaptı. Gerçek oturumda işin ortasında dizine bakmayı atlayabilir; bunu yalnız canlı deneme gösterir.
- Dizin yalnız adla çalışır: kötü adlandırılmış bir skill seçilmez. İşaret ("ne zaman" satırıyla) bunu kısmen telafi eder.
- İşi yalnız oturumun öncesinden anlaşılan isteklerde denemeler %36–41 verdi. Kelime eşleşmesine göre büyük artış, ama yarının altında.
- 3.000 karakter kabaca 45 skill tutar. Ötesinde bir kısmı dizinde görünmez ve yalnız işaretle gelir.
- Kelime eşleşmesinin yanlış işaretleri sürer (gerçek mesajlarda %14); bedeli artık tek satırdır.

## Yapana bırakılanlar

- Başlık ve yönerge cümlelerinin tam metni (İngilizce, ötekiler gibi).
- Hook'un okunan not yollarını sunucuya bildirme biçimi ve eski sürümlerle uyum (eski hook yeni sunucuyla, yeni hook eski sunucuyla çalışmaya devam etmelidir; biri eskiyse inceleme sorusu skill saymaz).
- "Gösterildi" kaydının koddan çıkarılma biçimi; durum dosyasında eskiden kalan "gösterildi" kayıtları okunmaz, dosya bozulmuş sayılmaz.
- Sabitlerin adları.

## Açık

- Halkadaki ikinci parçanın adı (proje sahibi).
