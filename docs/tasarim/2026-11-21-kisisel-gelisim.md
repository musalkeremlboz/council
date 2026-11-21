# Tasarım: kişisel gelişim

Tarih: 2026-11-21 · Durum: onaylandı (2026-11-21 04:39) · Hedef sürüm: 0.3.0

Ek tasarım `2026-11-21-skill-dizini.md` (onaylandı 2026-11-21 19:01, yapıldı) "Bağlama gelmesi", "İnceleme sorusu" ve "Ölçüm" bölümlerini değiştirir; değişen satırlar aşağıda işaretlidir.

Halkanın ikinci parçası. Birincisi hafızaydı.

## Amaç ve neden

Yardımcı, kullanıcıyla yaptığı işlerden kendiliğinden öğrenir: tekrar eden bir işin nasıl yapıldığını bir skill'e (belirli bir işin hazır tarifi) dönüştürür ve sonraki oturumlarda onu kullanır. Kullanıcı aynı şeyi iki kez anlatmaz, yardımcı aynı çözümü iki kez aramaz.

Bugün hafıza ne olduğunu hatırlıyor (kararlar, tercihler, düzeltmeler). Nasıl yapıldığını hatırlamıyor. Bir işin yolu bir oturumda bulunup öbüründe yeniden aranıyor.

COUNCIL'e özgü değer: öğrenilen şey tek bir yardımcıda kalmaz. Bir yardımcının çıkardığı skill, aynı hafızaya bağlı bütün yardımcılara gelir.

## Proje sahibinin kararları

1. Yardımcı öğrendiğini kullanıcıya sormadan kaydeder, tek satırla haber verir, kayıt geri alınabilir (2026-11-21 04:13).
2. Öğrenme incelemesi oturumun içinde yapılır; arka planda ayrı bir işte yapılmaz (04:25).
3. Özellik ancak testlerini ve ölçümlerini geçince eklenmiş sayılır ve halkadaki parçası dolar (03:36).
4. Sayfada ve görsellerde araç adı geçmez; özellik belirli bir yardımcıya göre anlatılmaz (03:36).

## Hedefler

- Tekrar eden işler ve zor bulunan çözümler skill olarak kaydedilir.
- Bir skill, konusu açıldığında hangi yardımcı olursa olsun bağlama gelir.
- Kullanıcı her öğrenmeyi görür ve tek cümleyle geri aldırabilir. Bu, skill'ler için de kurallara eklenen düzeltmeler için de geçerlidir.
- İşe yaramayan skill kendiliğinden ortadan çekilir; hafıza şişmez.
- Özelliğin işe yarayıp yaramadığı sayılarla görülür.

## Kapsam dışı (bu sürümde yapılmayacak)

- Arka plan incelemesi (yardımcının başsız kipini sohbet kaydı üzerinde çalıştırmak).
- Kendi öğrenme düzeneği olan yardımcıların skill'leriyle köprü.
- Skill'lerin yardımcıların kendi skill klasörlerine aktarılması.
- Anlam tabanlı eşleştirme. Eşleştirme bugünkü kelime aramasıyla yapılır.
- Oturum başında skill adlarının dizini. Dizinin yararı ancak bir model onu okuyup skill'i kendisi getirirse ortaya çıkar; bunu ölçecek düzenek yok. Gerçek kullanım verisi geldiğinde yeniden ele alınır. (Ek tasarımla değişiyor: `2026-11-21-skill-dizini.md`.)
- Düzeltmeyi sunucunun kendisinin fark etmesi. Neyin öğrenmeye değer olduğuna yardımcı karar verir.

## Olmaması gerekenler

Bunlardan biri oluyorsa özellik, teknik olarak çalışsa bile başarısızdır:

- Yardımcının dışarıdan okuduğu bir metin (web sayfası, belge, araç çıktısı) skill'e dönüşür.
- Bir skill'e şifre, erişim anahtarı ya da başka bir sır yazılır.
- Kullanıcı görmeden bir şey öğrenilir.
- Skill'ler bağlamı doldurup asıl notları dışarı iter.
- Kısa bir sohbet, öğrenme sorusuyla bölünür.
- Tek bir olaydan kalıcı bir kural çıkar.

## Yaklaşımlar

| Yol | Nasıl | Neden seçildi ya da seçilmedi |
|---|---|---|
| **Oturumun içinde** (seçilen) | İş bitince hafıza yardımcıya sorar, yardımcı o an kaydeder | Her yardımcıda çalışır, ek kurulum ve ek model ücreti yok. Bedeli: oturumu kısa süre meşgul eder. |
| Arka planda | Sohbetin kopyası ayrı bir işte incelenir | Kullanıcıyı meşgul etmez, ama COUNCIL'in model çalıştırmasını ve her yardımcı için ayrı bağlantıyı gerektirir. Sonraya bırakıldı. |
| Gece derlemesi | Zamanlanmış bir iş günün oturumlarını okur | Aynı bedel, üstüne gecikme. Seçilmedi. |

İncelenen örnek: kullanıcının kullandığı bir yardımcıdaki benzer düzenek (sayaçla tetiklenen arka plan incelemesi, klasör biçiminde skill, yazmadan önce okuma zorunluluğu, değişiklik defteri). Oradan alınanlar: sayaçla tetikleme, yazmadan önce okuma, tek satırlık bildirim. Alınmayan: ayrı değişiklik defteri, çünkü hafızadaki her değişiklik zaten git geçmişine işleniyor.

## Nasıl işler

```text
yardımcı cevabını bitirir
  → son incelemeden beri en az 15 araç çağrısı olduysa hafıza sorar:
    "bu işten öğrenilecek bir şey var mı?"
  → yardımcı karar verir:
      kullanıcı bir şeyi düzelttiyse   → kurallara tarihli tek satır
      tekrar eden ya da zor bulunan iş → skill (aday olarak)
      hiçbiri                          → hiçbir şey yazmaz
  → bir şey yazdıysa cevabının sonuna tek satır ekler: "Öğrendim: …"

sonraki oturumlar
  → kullanıcının mesajı bir skill'in konusuna uyuyorsa skill bağlama eklenir (ek tasarımla: skill'in metni değil, tek satırlık işaret; skill'i yardımcı açar)
  → inceleme sırasında yardımcı, o oturumda gelen skill'ler için bildirir: işe yaradı / yaramadı (ek tasarımla: yalnız açtığı skill'ler için)
  → ayrı oturumlarda üç kez işe yarayan aday kalıcı olur
  → beş ayrı oturum "işe yaramadı" deyip hiçbiri "yaradı" demediyse ya da iki kez "yanlış" dendiyse skill emekliye ayrılır
```

### Skill

Hafızada tek bir Markdown notu. Genel olanlar `skills/<ad>.md`, tek bir projeye ait olanlar `projects/<proje>/skills/<ad>.md` yolunda durur.

Sunucunun okuduğu etiketler sabittir ve İngilizcedir, çünkü hafızanın öteki sabit yapıları da öyledir (`## Active`, `## Closed`) ve biçim yayınlandıktan sonra değiştirmek pahalıdır. İçerik kullanıcının dilinde yazılır.

```markdown
# Servisi yeniden kurarken eski işi beklet

- **When:** Çalışan bir arka plan servisinin üstüne yeniden kurulum yapılırken
- **Status:** candidate
- **Source:** 2026-11-21, session 4cc0f9b3

## Steps
1. …

## Pitfalls
- …

## Learned from
Kullanıcının ne dediği ya da hangi işin bunu öğrettiği, bir iki cümle.
```

`When` satırı eşleştirmede en ağır basan yerdir. `Learned from` bölümü zorunludur: kaynağı gösterilemeyen skill yazılmaz. `Status` değerleri: `candidate`, `established`, `retired`.

### Araçlar

Yardımcının çağırdığı dört yeni araç. Adlar ve parametreler yapana bırakıldı; davranış şudur:

- **Düzeltmeyi kural olarak yaz.** Bugün düzeltmeler genel not düzenleme aracıyla yazılıyor ve sunucu bir düzeltmeyi başka bir düzenlemeden ayıramıyor. Öğrenilen düzeltme artık kendi aracından geçer: sunucu satırı `rules.md` (ya da projenin kural notu) içine tarihiyle ekler, öğrenme olarak sayar ve yeni satır var olan bir kuralla aynı konuda görünüyorsa bunu "olası tekrar" diye işaretler. Genel düzenleme aracı çalışmaya devam eder; onunla yazılan satır öğrenme sayılmaz.

- **Skill yaz ya da değiştir.** Yeni skill aday olarak doğar. Var olanı değiştirmek için, öteki notlardaki gibi, önce okunmuş olması ve sürüm özetinin geri verilmesi gerekir. Sunucu yazmadan önce denetler: zorunlu bölümler var mı, boyut sınırın altında mı, içinde sır gibi görünen bir şey var mı (anahtar, belirteç, özel anahtar bloğu, şifre ataması). Denetimi geçmeyen yazma reddedilir ve neden reddedildiği söylenir. Araç, kullanıcıya gösterilecek bildirim cümlesini döndürür.
- **Skill için geri bildirim ver.** İşe yaradı, yaramadı ya da yanlış. Sayaçlar kasanın dışında, veri klasöründe tutulur. Durum değişikliği (aday → kalıcı, → emekli) notun kendisine işlenir ve geçmişte görünür.
- **Son öğrenmeyi geri al.** Yeni yazılmış skill kaldırılır; değiştirilmiş skill bir önceki hâline döner; eklenen kural satırı çıkarılır. Git geçmişi kullanılır, hiçbir şey kalıcı olarak silinmez.

Emekli skill `skills/retired/` altına taşınır: aranabilir, ama bağlama eklenmez. Emeklilik hem adaylar hem kalıcılar için geçerlidir. Emekli bir skill, aynı adla yeniden yazıldığında aday olarak geri döner.

Emeklilik süreye değil kanıta bağlıdır. Seyrek yapılan bir işin skill'i aylarca hiç gelmeyebilir; bağlama gelmediği sürece yer tutmaz ve bekler (ek tasarımla: dizinde tek satır tutar). Bir skill'in yalnızca gösterilmiş olması da onu emekli etmez: kısa oturumlarda ve hook'u olmayan yardımcılarda geri bildirim hiç sorulmaz, sorulmayan oturum "yaramadı" demiş sayılamaz. Emekli olan, beş ayrı oturumun "işe yaramadı" dediği ve hiçbirinin "yaradı" demediği skill'dir. (Yapım sırasında değişti: ilk tasarım beşinci gösterimde emekli ediyordu ve o oturum daha cevap veremeden skill çekiliyordu.)

Oturum kimliği bildirmeyen yardımcıların geri bildirimi gün başına bir oturum sayılır.

Skill klasöründeki her not skill değildir. Bir not ancak eksiksizse (başlık, `When`, `Steps`, `Learned from`), durumu `candidate` ya da `established` ise ve sır denetiminden geçiyorsa skill sayılır. Bu koşulları tutmayan not sıradan bir nottur: sıradan notlar gibi bağlama gelir, skill olarak önerilmez. Böylece kullanıcının `skills/` adlı klasöründe zaten duran notlar çalışmaya devam eder ve denetimden geçmemiş bir not skill diye sunulamaz.

### Bağlama gelmesi

- **Her mesajda:** bugünkü ilgili not aramasına ek olarak mesaj, canlı skill'lerin hepsiyle tek tek karşılaştırılır. En çok iki skill, ayrı bir başlık altında ve ayrı bir bütçeyle (1.500 karakter) eklenir. Notların bütçesinden yemez. Aynı skill bir oturumda bir kez gönderilir.
- **Eşleştirme kuralı:** yine kelime tabanlıdır. Mesajdaki anlamlı kelime köklerinden kaçının skill'de geçtiğine bakılır. Aynı kelimenin çekimli biçimleri tek kelime sayılır. Başlıkta ve `When` satırında geçen kelime dört kat sayılır, az sayıda skill'de geçen kelime daha çok sayılır. Toplam, mesajdaki kelime sayısının kareköküne bölünür; böylece uzun bir mesaj yalnız uzun olduğu için eşleşmez. Bir skill ancak mesajın en az iki ayrı kelimesi başlığında ya da `When` satırında geçiyorsa ve puanı eşiği geçiyorsa önerilir; yalnız gövdede geçen kelimeler bir skill'i tek başına getirmez. (2026-11-21'de gerçek mesajlarla ölçümden sonra değişti; önceki kural kökleri tek tek sayıyor, gövdeyi de eşleşme sayıyor ve mesaj uzunluğuna bakmıyordu.) (Yapım sırasında değişti: arama indeksinin puanı az sayıda notta güvenilir çıkmadı ve notlar çoğaldıkça skill'ler aday listesine giremiyordu.)
- Skill tarafındaki hiçbir hata sıradan notların gelmesini engelleyemez; hata kayda geçer ve o mesajda skill eklenmez.
Emekli ve denetimden geçmemiş skill'ler hiçbir zaman eklenmez.

### İnceleme sorusu

Yardımcı cevabını bitirirken çalışan hook, bugün "kaydedilmemiş iş var" hatırlatmasını yapıyor. İnceleme sorusu aynı hatırlatmaya eklenir; yardımcı iki kez durdurulmaz.

Soru yalnız şu durumda sorulur: son incelemeden beri en az 15 araç çağrısı yapılmışsa. Kısa sohbetlerde hiç sorulmaz. 15 başlangıç değeridir, ayardan değiştirilebilir.

Soru, o oturumda bağlama eklenen skill'leri adıyla sayar ve her biri için geri bildirim ister.

Hook'u olmayan yardımcılar için aynı yönerge sunucunun kullanım yönergelerine yazılır. Onlarda tetik daha zayıftır; bu bilinen bir sınırdır.

### Bildirim

Bir şey yazıldıysa yardımcı cevabının sonuna tek satır ekler: ne öğrendiği ve geri almak için ne denmesi gerektiği. Kullanıcı "onu geri al" dediğinde yardımcı geri alma aracını çağırır.

### Korumalar ve sınırları

- Sır denetimi sunucuda yapılır ve yazmayı engeller.
- "Yalnız kullanıcının sözlerinden ve yapılan işten öğren" kuralı yönergeyle verilir, kaynak bölümü zorunlu tutulur ve bildirim satırı her öğrenmeyi kullanıcıya gösterir. Sunucu bunu kendi başına doğrulayamaz. Sınır budur ve belgelerde açıkça yazılır.
- Tek olaydan kalıcı kural çıkmasını aday aşaması önler: aday da bağlama gelir, ama üç ayrı oturumda işe yaramadan kalıcı olmaz ve kullanılmazsa çekilir.

## Ölçüm ve "tamam" ölçütü

Halkadaki parça, üçü de tutunca dolar:

1. **Eşleştirme testi.** Bir skill kümesi ve bir kullanıcı mesajı verilir; isabet, doğru skill'in bağlama eklenen en çok iki skill'in arasında olmasıdır. Konusu olan mesajlarda isabet en az %80, konu dışı mesajlarda herhangi bir skill'in gelme oranı en çok %20. İki ayrı küme vardır:
   - **Depodaki küme:** uydurma, en az 20 konulu ve 10 konu dışı senaryo. Her değişiklikte çalışır, geriye gidişi yakalar.
   - **Ayrı tutulan küme:** proje sahibinin kendi kurulumundaki gerçek mesajlardan ve onun gerçek iş tariflerinden kurulur, depoya girmez, eşik ayarlanırken kullanılmaz ve ölçüt için bir kez ölçülür. Ölçütü tutturan sayı bu kümeninkidir. Böylece testi yazan, kendi testine göre ayar yapmış olmaz.
2. **Gerçek kullanım, iki hafta.** Proje sahibinin kendi kurulumunda. Aynı düzeltmenin ikinci kez yapılması gerekmez. Sunucunun "olası tekrar" diye işaretlediği satırlar iki haftanın sonunda tek tek elle incelenir; doğrulanmış tek bir tekrar ölçütü düşürür.
3. **Yanlış öğrenme oranı.** Aynı iki haftada geri alınan öğrenmeler (skill ve kural birlikte), toplam öğrenmenin %20'sinden azdır.

Depodaki kümenin sonucu (2026-11-21, 14 skill, 28 konulu ve 14 konu dışı mesaj): konulu %89 (25/28), konu dışı %0 (0/14). Aynı ölçüm 1, 2, 3, 6 ve 14 skill'lik kütüphanelerde ayrı ayrı yapılır ve hepsinde sınırların içindedir. Küme, eşleştirme kodunu görmeyen ayrı bir yazar tarafından yazıldı; kuralı: her mesaj, ait olduğu skill'le aynı dildedir, çünkü skill kullanıcının dilinde yazılır. Dil karışık kullanımda eşleşme zayıftır; bu bilinen bir sınırdır ve ayrı tutulan kümeyle ölçülecektir.

Ayrı tutulan kümenin sonucu (2026-11-21, bir kez ölçüldü): proje sahibinin 201 gerçek mesajı ve notlarındaki iş tariflerinden yazılan 34 skill. Skill'leri ve etiketleri, eşleştirme kodunu görmeyen iki ayrı yazar hazırladı; kural ölçümden önce yazıldı. **Konulu %80 (20/25), konu dışı %39 (51/132): 1. ölçüt tutmadı.** Oturumun öncesi bilinmeden anlaşılmayan mesajlarda doğru skill 44'te 4 kez geldi (%9; ölçüte girmez). Neden: puan, mesajdaki eşleşen köklerin toplamıdır ve mesaj uzadıkça büyür. Konu dışı mesajlarda yanlış öneri 80 karakterin altında 78'de 6, 160 karakterin üstünde 27'de 26. Depodaki kümenin konu dışı mesajlarının hepsi kısa olduğu için bunu göstermedi. Bu küme artık görülmüş sayılır; düzeltmeden sonraki ölçüt sayısı yeni gerçek mesajlarla alınır.

Düzeltmeden sonra (2026-11-21, aynı gün): aynı kümede konulu %72 (18/25), konu dışı %14 (18/132). Bu bir geliştirme sayısıdır, ölçütün sayısı değildir: kural bu kümeye bakılarak seçildi. Uzun mesajlardan oluşan ve eşleştirme kodunu görmeyen bir yazarın yazdığı ikinci depo kümesinde (`tests/scenarios/skills_long.json`, 150–650 karakter): konulu %71 (20/28), başka konudaki mesajlarda %14 (2/14), bir skill'in konusunda olup başka bir şey isteyen mesajlarda %57 (8/14). Önceki kural aynı kümede konu dışı 28 mesajın 27'sinde skill öneriyordu. Kısa mesajlı ilk kümede sonuç değişmedi (%89, %0).

Kalan iki sınır kelime eşleştirmesinin kendisinden gelir ve eşik ayarıyla kapanmaz: (1) kelimeler mesajın konusunu gösterir, ne istendiğini göstermez; skill'in konusunda geçen ama o işi istemeyen mesajlara da skill gelir. (2) Skill'in başlığıyla iki kelime paylaşmayan istekler ("bunu da yükle", başka sözcüklerle anlatılan aynı iş) yakalanmaz; yalnız oturumun öncesinden anlaşılan isteklerde oran %5'tir (2/44). Konulu oran %80 sınırının altındadır.

Bilinen sınır: 10'dan çok skill olduğunda nadirlik puanı kütüphane büyüdükçe artar ve eşik görece kolaylaşır. Onlarca skill'e ulaşıldığında ölçüm yinelenmelidir.

`council usage` çıktısına öğrenme özeti eklenir: sorulan inceleme, yazılan skill ve kural, kalıcı olan, emekli olan, geri alınan, işe yarama oranı, olası tekrarlar.

## Aşamalar

1. **Depo ve eşleştirme.** Skill notları, dört araç, denetimler, bağlama ekleme, eşleştirme testi. İnceleme sorusu yok. Bu aşamanın sonunda 1. ölçüt ölçülür.
2. **İnceleme sorusu ve bildirim.** Hook'a ve sunucu yönergelerine eklenir. Emeklilik ve kalıcılık kuralları çalışır.
3. **Gerçek kullanım.** Proje sahibinin kurulumu yeni sürüme geçirilir ve iki hafta ölçülür. O kurulum bugün eski bir sürümde ve canlı hafızayı taşıyor; geçiş ayrı bir onayla yapılır.
4. **Yayın.** Ölçütler tutarsa sürüm 0.3.0 yayınlanır, halkadaki parça dolar, sayfaya özelliğin bölümü eklenir.

## Yapana bırakılanlar

- Araçların adları, parametreleri ve dönüş biçimleri.
- İnceleme sorusunun ve yönergelerin sözleri.
- Skill'in boyut sınırı ve sır denetimindeki kalıplar.
- Sayaçların veri klasöründeki saklanma biçimi.
- Eşleştirmede `When` satırına verilecek ağırlığın ve puan eşiğinin nasıl uygulanacağı.
- "Olası tekrar" işaretinin hangi benzerlik kuralıyla konacağı.

## Açık

- Parçanın halkadaki adı. Kullanıcı "kişisel gelişim" diyor; halkaya yazılacak tek sözcük henüz seçilmedi.
