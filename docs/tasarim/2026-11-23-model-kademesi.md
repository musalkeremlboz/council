# Model kademesi: yönetici model işi bir alt kademeye dağıtır

**Durum:** proje sahibi onayladı (2026-11-23 21:59, "Onaylıyorum"). Yapım planı: `2026-11-23-model-kademesi-plan.md`. Kod yazılmadı.
**Ad:** "model kademesi" geçici addır; halkadaki tek sözcüklük adı proje sahibi koyacak.
**Dal ve sürüm:** çalışma `main`'den açılan `model-kademesi` dalında yapılır. Sürüm numarası yayında belirlenir (bugün yayınlanmış sürüm 0.2.1; 0.3.0 henüz çıkmadı). `main`'e birleşme ve yayın ayrı onayla.

## Amaç ve neden

Bugün bir oturumda başlatılan alt ajan, aksi söylenmedikçe ana sohbetin modeliyle çalışır. Ana sohbet en üst modeldeyse dosya okuma, arama, test çalıştırma gibi işçilik de en üst modelin fiyatıyla yapılır.

Proje sahibinin istediği: ana sohbetteki model yönetici olsun; çok işli bir istemde işleri bir alt kademedeki modelle çalışan alt ajanlara dağıtsın ve gelen sonucu denetlesin. Kazanç iki yönlü: daha az harcama, ve proje sahibinin tek bir sohbetten işi yönetebilmesi.

(Alt ajan: ana sohbetin bir iş için başlattığı, kendi bağlamıyla çalışan ve sonunda kısa bir rapor döndüren ikinci oturum. Hook: yardımcının belirli anlarda kendiliğinden çalıştırdığı küçük program; hafıza bağlamını bugün o getiriyor.)

## Proje sahibinin kararları

- 2026-11-23 21:45 · Üçüncü ana özellik bu. Örnekleri: ana sohbet Fable 5.2 ise alt ajanlar Opus 5.5; ana sohbet Opus 5.5 ise alt ajanlar Sonnet 5.5. "Fable 5.2 (Mythos 5.2) bir işçi değil": direktif veren ve sonucu denetleyen olmalı.
- 2026-11-23 21:45 · Önce dört modelin hangi işe uygun olduğu değerlendirilsin, sonra sistem kurulsun.
- 2026-11-23 21:49 · "O zaman dediğin gibi ilerleyelim": yönetici küçük ve tek işi kendi yapar, çok ve bağımsız ya da hacimli işi dağıtır; varsayılan bir alt kademedir, basit iş daha aşağıya verilebilir, yukarıya verilemez; ilk sürüm alt ajan çalıştırabilen Claude oturumlarında (Mac ve sunucu); değerlendirme kurulumdan önce gerçek işlerle küçük bir denemeyle sınanır.

## Dört modelin değerlendirmesi

Fiyatlar Anthropic'in liste fiyatıdır (1 milyon token, girdi / çıktı; 2026-11-03 tarihli kopya). Uygunluk sütunu Anthropic'in model rehberinden çıkarıldı; proje sahibinin işlerinde ölçülmedi.

| Kademe | Model | Fiyat | Uygun olduğu iş | Uygun olmadığı iş |
|---|---|---|---|---|
| 4 | Fable 5.2 (Mythos 5.2) | 8 $ / 40 $ | Planlama, belirsiz ve uzun iş, işi parçalara bölme, sonucu denetleme | Okuma, arama, tarifli uygulama gibi işçilik (pahalı ve yavaş) |
| 3 | Opus 5.5 | 4 $ / 20 $ | Zor kodlama, çok adımlı uygulama, tasarım kararı isteyen parça | Toplu okuma ve arama |
| 2 | Sonnet 5.5 | 2 $ / 10 $ | İyi tarif edilmiş gündelik kodlama, test, belge | Tarifi eksik, karar isteyen iş |
| 1 | Haiku 5.5 | 0,10 $ / 0,50 $ | Arama, okuyup özetleme, sınıflandırma, çıktısı kolay denetlenen toplu iş | Uzun, çok adımlı ajan işi |

Tasarımı belirleyen bulgu (Anthropic'in ölçümleri): dağıtmak yalnız hacimli ve birbirinden bağımsız işlerde kazandırıyor (yaklaşık yarı maliyet, bir miktar düşük puanla). Tek parça ya da küçük işte her alt ajan bağlamı baştan kurduğu için, yönetici modelin işi kendisinin yapması daha ucuz ve daha hızlı çıkıyor. Bu yüzden kural "her işi dağıt" değil.

Bugünkü durum (proje sahibinin Mac'indeki 127 alt ajan kaydından sayıldı, 2026-11-23): 33'ü ana sohbetin modeliyle, yani en üst kademede çalışmış (hepsi genel amaçlı ajan; 24'ünde model hiç belirtilmemiş, 9'unda en üst model açıkça istenmiş). Kalanı Sonnet 68, Opus 15, Haiku 11. Zorlamanın hedefi bu 33'tür.

Bu oturumdan bir örnek (ölçüldü): ana sohbet yaklaşık 27 bin çıktı tokenı ve 3,3 milyon önbellekten okunan token harcadı; belge araştırmasını yapan alt ajan (Haiku) 6,5 bin çıktı ve 78 bin okuma. Harcamanın büyüğü, uzun bağlamın her araç çağrısında yeniden okunması. Araç çağrısı çok olan işi kısa bağlamlı ve ucuz bir işçiye vermek tam bunu azaltır.

## Hedefler

- Çok ve bağımsız ya da hacimli iş, ana modelin bir alt kademesinde çalışan alt ajanlara gider.
- Hiçbir alt ajan ana modelin kademesinde ya da üstünde çalışmaz (aşağıdaki "fork" istisnası dışında).
- Yönetici, işçinin sonucunu kullanmadan önce denetler ve proje sahibine neyi kime verdiğini tek satırla söyler.
- Kazanç ölçülür: hangi model ne kadar harcadı, liste fiyatıyla ne etti.
- Kapatmak tek ayardır.

## Kapsam dışı (bu sürümde yapılmayacak)

- Hook'u olmayan yardımcılar, Hermes, Antigravity, telefon ve web. Bunlarda alt ajan ya yok ya da başka bir düzenekle çalışıyor; her biri ayrı iştir.
- Sunucu tarafında değişiklik. Bu sürüm yalnız yardımcının yanındaki hook'ta ve komut satırında yaşar (neden: "Yaklaşımlar").
- Alt ajanın düşünme düzeyini (effort) ayarlamak.
- İşçiye hafızadan kural ve not taşımak (aşağıda "İşçi ve hafıza").
- Panelde gösterim.
- Çok ajanlı betik araçları (Workflow gibi): alt ajanı başka yoldan başlatıyorlar, bu hook'tan geçip geçmedikleri bilinmiyor.

## Olmaması gerekenler

- Küçük ve tek bir işin dağıtılması (süre ve harcama artar).
- Hook yüzünden bir alt ajan çağrısının başarısız olması, gecikmesi ya da izin sorusunun değişmesi.
- Kendi daha ucuz modeli olan bir ajan türünün yukarı çekilmesi.
- Yöneticinin, işçinin yaptığı işi baştan kendisinin yapması (çifte harcama).
- Proje sahibinden habersiz model değişimi.
- Sunucuda süren canlı denemenin (21.11 → 05.12.2026) koşullarının sessizce değişmesi.

## Yaklaşımlar

1. **Yalnız yönerge.** Oturum başında modele ne zaman dağıtacağı ve hangi modele vereceği söylenir. Basit; ama uyup uymadığı modele kalır, unuttuğunda alt ajan ana modelin fiyatıyla çalışır.
2. **Yalnız zorlama.** Hook her alt ajan çağrısında modeli bir alt kademeye çeker. Kesin; ama neyin dağıtılacağını ve sonucun nasıl denetleneceğini söylemez.
3. **Yönerge + zorlama + ölçüm (seçilen).** Yönerge kararı yönlendirir, hook kademeyi garanti eder, rapor kazancı gösterir. Proje sahibi yapım yolunu Claude'a bıraktı ("dediğin gibi ilerleyelim"); seçim Claude'un.

Elenenler: sabit ortam değişkeni (alt ajan modelini ana modele göre değiştiremez); ajan tanım dosyaları (çağrıdaki model seçimi tanımdaki modeli ezer, ayrıca her bilgisayara dosya dağıtmak gerekir).

Yönergenin sunucudan değil hook'tan gelmesi Claude'un kararıdır: kademe Claude modellerine özgüdür, sunucu ise bütün yardımcılara aynı hizmeti verir. Böylece sunucu değişmez, canlı deneme etkilenmez ve sunucu kurulumu gerekmez.

## Nasıl işler

### Kademe sırası

Model kimliğindeki aile adına bakılır: `fable` ya da `mythos` 4, `opus` 3, `sonnet` 2, `haiku` 1. Sürüm numarasına bakılmaz; yeni sürüm çıkınca kod değişmez. Aile adı tanınmıyorsa kademe "bilinmiyor"dur ve hook hiçbir şeye dokunmaz. Alt ajan çağrısında kullanılan kısa adlar aynıdır: `fable`, `opus`, `sonnet`, `haiku`.

### Ana modelin öğrenilmesi

Hook her çalıştığında oturum kaydının yolunu alır (bugünkü hook iş bitimindeki denetimde bu dosyayı zaten okuyor). Kayıttaki son yardımcı mesajının `message.model` alanı ana modeldir (bu oturumda doğrulandı: `claude-mythos-5-2`). Oturum ortasında model değişirse sonraki mesajla birlikte kendiliğinden doğru değer okunur. Dosya büyük olabileceği için sondan okunur. Değer bulunamazsa kademe "bilinmiyor"dur.

### Yönerge (oturum başı)

Hook, oturum başında hafıza bağlamının sonuna sabit bir blok ekler (özellik kapalı değilse). Blok ana modele göre değişmez; bütün kademeyi söyler. Böylece oturum ortasında model değişse de eskimez ve hook'un oturum başında modeli bilmesi gerekmez. Metin, hook'un öteki yönergeleri gibi İngilizcedir. Taslak (yapan sözleri düzeltebilir, anlamı değiştiremez; en çok 1.200 karakter):

```
[Delegation] Sub-agents here run one tier below the session's model: fable/mythos -> opus,
opus -> sonnet, sonnet -> haiku. A hook enforces the ceiling.
- Do it yourself: one small task, a quick lookup, steps that depend on each other, anything
  that needs this conversation to judge. Handing these off costs more time and tokens.
- Hand off: two or more independent pieces of real work, or one bulky piece (wide reading,
  many files, a long tool loop) whose result fits in a short report. Start independent
  workers in the same turn.
- A simpler piece may go lower than the default: searching, reading, summarising -> haiku;
  well-specified code, tests, docs -> sonnet. Never higher.
- Brief each worker once and fully: goal, files, what is known, what done looks like, what
  to return. It sees neither this conversation nor the memory context.
- Check a worker's result itself (the diff, the test output, the file) against what the
  user asked before relying on it. Do not redo its work.
- Tell the user in one line what you handed off and to which model.
- A fork runs on your own model; use a fresh agent for handed-off work.
```

Proje sahibinin kişisel ayarları ("test yazmayı şu modele verme" gibi) yeni bir düzenek istemez: düzeltme olarak kurallara yazılır (ikinci özellik) ve kurallar her oturum başında zaten bağlama gelir.

### Zorlama (alt ajan çağrısında)

Hook, alt ajan başlatan araç çağrısından hemen önce çalışır (olay `PreToolUse`, araç adı `Agent`, eski adı `Task`). Ağa çıkmaz. Karar:

1. Özellik `off` ya da `advise` ise ya da ana modelin kademesi bilinmiyorsa: dokunma.
2. Tavan = ana modelin kademesi − 1; en alt kademedeki oturumda tavan o kademenin kendisidir (altı yok, ama yukarısı yine verilemez). (Plan yazılırken netleşti, 2026-11-23: onaylanan metin en alt kademede "dokunma" diyordu; bu, "yukarıya verilemez" kararıyla çelişiyordu.)
3. Çağrıda model yazıyorsa: kademesi tavandan yüksekse tavana indir; değilse olduğu gibi bırak (yönetici daha aşağıyı seçmiş olabilir).
4. Çağrıda model yazmıyorsa: ajan türü ana modeli devralan türlerdense tavanı yaz; kendi modeli olan türlerde dokunma.
   - Devralan türler: tür belirtilmemiş ve `general-purpose` (yerel kayıtlarda doğrulandı: modeli belirtilmeyen 24 çağrının hepsi ana modelle çalışmış); ayrıca kullanıcının ya da projenin ajan klasöründe (`~/.claude/agents`, `<proje>/.claude/agents`) tanım dosyası bulunan ve o dosyada `model:` satırı olmayan ya da `inherit` yazan türler.
   - `claude`, `Plan` ve `Explore` belgelere göre ana modeli devralıyor, ama yerel kayıtlarda örnekleri yok. Sonda bunları tek tek dener; ana modeli devraldığı görülen tür listeye girer, görülmeyen girmez.
   - Tanınmayan her tür (eklenti ajanları dahil): dokunma. Yanlışlıkla ucuz bir ajanı yukarı çekmektense tavanı uygulamamak yeğdir. (Yerel kayıtlarda belge rehberi ve sayfa okuma ajanları Haiku ile çalışıyor.)
5. Tür `fork` ise dokunma: yardımcı fork'ta model seçimini yok sayıyor.
6. Çağrı bir alt ajanın içinden geliyorsa dokunma (ayırt edilebiliyorsa; bkz. "Sonda").

Hook modeli değiştirdiğinde işçinin istemine şu tek satırı da ekler: `COUNCIL memory is readable with council_search and council_read. Do not write to it; the session that started you records the work.`

Hook her kararı yerel bir kayda tek satır olarak yazar (`~/.council/state/delegation.jsonl`: zaman, oturum, ajan türü, istenen model, yazılan model, neden). Hook'un herhangi bir hatası ya da zaman aşımı çağrıyı olduğu gibi geçirir. İzin kararına dokunulmaz: hook yalnız girdiyi değiştirir, "izin ver" demez.

### Ayar

`~/.config/council/config.json` içinde `"delegation"`: `"enforce"` (varsayılan; yönerge + zorlama), `"advise"` (yalnız yönerge), `"off"` (hiçbiri).

### İşçi ve hafıza

İşçi hafıza bağlamını görmez (oturum başı ve mesaj hook'ları alt ajanda çalışmıyor); hafıza araçlarına ise erişebilir. Bu sürümde işçiye kural ya da not taşınmaz: yönetici, işçinin parçasını ilgilendiren kuralı brife kendisi yazar ve sonucu kurallara göre denetler. Neden: taşımak her alt ajan çağrısına bir ağ isteği ve birkaç bin karakter ekler; yararı ölçülmeden eklenmemeli. Canlı denemede işçi kaynaklı bir kural ihlali görülürse sonraki sürümün konusu olur. İşçi hafızaya yazmaz; oturum kartını ve günlüğü yönetici yazar.

### Rapor

Yeni komut: `council delegation report --days 14` (yardımcının kayıtlarının durduğu bilgisayarda çalışır; sunucuya bağlanmaz). Okudukları: `~/.claude/projects/` altındaki oturum kayıtları, her oturumun `subagents/` klasöründeki alt ajan kayıtları ve hook'un karar kaydı. Alt ajanın **gerçekte çalıştığı model**, kendi kaydındaki (`agent-*.jsonl`) yardımcı mesajlarının `message.model` alanından okunur. `agent-*.meta.json` yalnız ajan türünü ve *istenen* modeli verir: 127 yerel kaydın 25'inde model alanı yok, çoğunda kısa ad var; ihlal sayımında ona güvenilmez. Bir alt ajanın karşılaştırılacağı ana model, ana kayıtta o alt ajanın ilk satırından önceki son yardımcı mesajının modelidir. İhlal: alt ajanın gerçek kademesi o andaki tavandan yüksek (tavan hook'taki kuralla aynı; fork ayrı sayılır). Gösterdikleri, ana modelin kademesine göre ayrı ayrı:

- oturum sayısı, alt ajan çağrısı sayısı; hook'un indirdiği, yazdığı ve dokunmadığı çağrılar;
- her model için token (girdi, çıktı, önbellekten okuma, önbelleğe yazma) ve liste fiyatıyla karşılığı;
- harcamanın ana kademenin altında yapılan payı;
- ana modelin kademesinde ya da üstünde çalışmış alt ajanlar (ihlal; fork ayrı sayılır);
- "küçük iş dağıtımı" göstergesi: beşten az araç çağrısıyla biten alt ajanların payı;
- tahmini kazanç: alt ajanların tokenları ana modelin fiyatıyla ne ederdi, eksi gerçekte ne etti. Bu bir üst sınır tahminidir, öyle etiketlenir: aynı işi ana model başka sayıda tokenla yapardı.

Fiyatlar paketteki küçük bir tablodan okunur (tarihiyle); abonelikte gerçek fatura değil, modelleri birbirine oranlamak için ağırlıktır. Aynı mesaj kimliği kayıtta birden çok satırda geçebilir; token bir kez sayılır.

### Kurulum

- `council install`, ayar dosyasına dördüncü hook kaydını ekler (`PreToolUse`, eşleşme `Agent|Task`, zaman aşımı 5 sn). Bugünkü kayıt biçiminde eşleşme alanı yok; kurucu buna göre genişletilir.
- **Var olan kurulumlar:** güncellemeyi eski sürümün kodu yürütür; o kod yeni kaydı eklemeyi bilmez, yalnız hook dosyasını kopyalar. Bu yüzden eksik kaydı, güncellemeden sonra yeniden başlayan servis açılışta tamamlar (yalnız COUNCIL'in öteki hook'ları ayar dosyasında zaten varsa; yedek alarak; ayar dosyası bozuksa dokunmadan). Kayıt eklenene kadar özellik yalnız yönerge olarak çalışır.
- Kaldırma bu kaydı da siler. `council status` bugün "hook'lar kurulu" demek için bütün kayıtları arıyor; üç kayıtlı eski kurulumlar "kurulu değil" görünmesin diye hafıza hook'ları ile bu kayıt ayrı satırlarda bildirilir, ve özelliğin açık, yalnız yönerge ya da kapalı olduğu söylenir.
- Proje sahibinin Mac'i ve sunucudaki Claude elle kurulmuş düzenlerdir: hook dosyası yenilenir ve ayar dosyasına kayıt eklenir (yedek alınarak). Her biri ayrı onayla.

## Sonda (yapımın ilk işi)

Aşağıdakiler belgelerden okundu, çalışırken görülmedi. Kod yazılmadan önce, ayar dosyası ayrı verilen kısa bir deneme oturumuyla (ucuz modelle, proje sahibinin gerçek ayarlarına ve hafızasına dokunmadan) doğrulanır; sonuçlar bu belgeye yazılır:

1. `PreToolUse` hook'u alt ajan çağrısında çalışıyor mu; girdide hangi alanlar var (`subagent_type`, `model`, `prompt`; çağrının bir alt ajandan gelip gelmediğini gösteren bir alan).
2. `updatedInput`, izin kararı verilmeden modeli değiştiriyor mu; izin sorusu aynı kalıyor mu. Alt ajanın gerçekte hangi modelle çalıştığı kendi kaydındaki `message.model`'den okunur.
3. Hook çalıştığı anda oturum kaydında o turun yardımcı mesajı yazılmış mı (ilk turda ana model okunabiliyor mu). Okunamıyorsa yedek: oturum başı girdisindeki `model` alanı durum dosyasına yazılır.
4. `claude`, `Plan` ve `Explore` türleri model belirtilmeden çağrıldığında hangi modelle çalışıyor.
5. Masaüstü uygulamasında da aynı mı.

Sonda bir maddeyi çürütürse o parça yeniden tasarlanır ve proje sahibine bildirilir. En kötü durumda (model değiştirilemiyorsa) özellik "yalnız yönerge" olarak kalır ve bu açıkça söylenir.

## Ölçüm ve "tamam" ölçütü

1. **Zorlama (kesin).** Testlerde her (ana model, çağrı) çifti beklenen modele çevrilir. Canlıda iki hafta boyunca raporda ihlal sayısı 0'dır (fork hariç).
2. **Davranış.** İki haftalık gerçek kullanımda küçük iş dağıtımı göstergesi %20'nin altındadır; proje sahibinin "bunu dağıtmamalıydın" ya da "bunu dağıtmalıydın" düzeltmeleri kurala yazılır ve aynı düzeltme tekrarlanmaz.
3. **Kazanç (karşılaştırmalı deneme, ayrı onayla).** Proje sahibinin gerçek işlerinden seçilen üç çok parçalı iş, her biri iki kez yapılır: özellik açık ve kapalı. Liste fiyatıyla harcama en az %20 düşer; sonuç proje sahibince kabul edilir kalır; süre uzamaz. Bu deneme gerçek kullanım hakkı harcar; başlamadan önce tahmini bedeli söylenir.

Üçü de tutmadan özellik "tamam" sayılmaz. Tutmayan ölçüt düşürülmez; neden aranır.

## Aşamalar

1. Sonda.
2. Hook: kademe, ana modelin okunması, karar, karar kaydı, yönerge bloğu; testler.
3. Kurulum, kaldırma, durum; rapor komutu; testler (Linux, macOS, Windows).
4. Proje sahibinin Mac'inde açma (onay). Sunucuda süren ikinci özellik denemesinin değerlendirmesine (05.12) açılış tarihi not düşülür: ana sohbette araç çağrısı azalacağı için inceleme sorusu daha seyrek gelebilir.
5. Sunucudaki Claude'da açma (onay).
6. İki haftalık kullanım ve karşılaştırmalı deneme (onay).
7. `main`'e birleşme ve yayın (onay).

## Sınırlar

- Dağıtıp dağıtmama kararı modelindir; yönerge bunu yönlendirir, garanti etmez. Hook yalnız modeli sınırlar.
- Fork ana modelle çalışır; engellenemez, yalnız yönergeyle caydırılır.
- Bir alt kademe, işi ana model kadar iyi yapmayabilir. Buna karşı iki şey var: yöneticinin denetimi ve karşılaştırmalı deneme.
- Tahmini kazanç gerçek karşılaştırma değildir; gerçek karşılaştırma yalnız 3. ölçütteki denemedir.
- Uygunluk tablosu belgelerden çıkarıldı; proje sahibinin işlerinde ölçülmedi.
- İşçi hafıza bağlamını görmez; kurallara uyum yöneticinin brifine ve denetimine bağlıdır.

## Yapana bırakılanlar

- Yönerge bloğunun son sözleri (anlam ve 1.200 karakter sınırı içinde).
- Oturum kaydının sondan okunma biçimi; karar kaydının büyüyünce kırpılması.
- Ajan tanım dosyasındaki `model:` satırının okunması (basit satır okuma yeter).
- Raporun çıktı düzeni ve `--json` seçeneği.
- Dosya ve işlev adları (öneri: mantık `council/hook.py` içinde kalır, rapor `council/delegation.py`).

## Açık

- Özelliğin halkadaki adı (proje sahibi).
- Karşılaştırmalı denemede kullanılacak üç iş (proje sahibiyle seçilir).

## Sonda sonuçları (2026-11-23 22:15)

Üç kısa deneme oturumu, masaüstü uygulamasının içindeki istemciyle (2.1.328), boş bir geçici projede, yalnız proje ayarları yüklenerek (`--setting-sources project`) çalıştırıldı. Proje sahibinin hafıza hook'ları bu oturumlarda çalışmadı; süren denemenin sayılarından düşülecek bir şey yok. Liste fiyatıyla toplam bedel yaklaşık 0,24 $.

1. **Hook alt ajan çağrısında çalışıyor.** Araç adı `Agent`. Girdideki alanlar: `session_id`, `transcript_path`, `cwd`, `permission_mode`, `effort`, `prompt_id`, `tool_use_id`, `tool_name`, `tool_input` (`description`, `prompt`, `subagent_type`, isteğe bağlı `model`, `run_in_background`). Girdide ana modelin adı **yok**.
2. **Model değişiyor, izin değişmiyor.** Hook `updatedInput` ile `sonnet` isteğini `haiku`ya çevirdi, `permissionDecision` vermedi; alt ajan gerçekten Haiku ile çalıştı (kendi kaydındaki `message.model`), izin reddi ya da ek soru olmadı. Ana kayıt ise çağrıyı ilk hâliyle (`sonnet`) saklıyor: gerçek model yalnız alt ajanın kendi kaydından okunabilir.
3. **İlk turda kayıtta yardımcı mesajı henüz yok**; tasarımdaki yedek de yok: oturum başı girdisinde `model` alanı gelmiyor (alanlar: `cwd`, `session_id`, `source`, `transcript_path`). Ama kayıtta, yanıt gelmeden önce yazılan bir **istek satırı** var (`type: "api-request"`, modeli `params.model`); hook çalıştığı anda o satır yerindeydi. Yerel 52 oturum kaydının hepsinde bu satırlar var ve modelleri her zaman ana sohbetin modeli. **Karar (Claude):** ana model, kayıttaki son yardımcı mesajından *ya da* son istek satırından, hangisi daha sondaysa ondan okunur. Böylece ilk turda ve oturum ortasındaki model değişiminde de doğru değer bulunur. İstek satırı belgelenmiş bir biçim değil; bulunamazsa hook dokunmaz (ilk turdaki çağrı tavansız kalır, yönerge yine geçerlidir).
4. **`claude`, `Plan` ve `Explore` ana modeli devralıyor.** Ana model Sonnet iken üçü de model belirtilmeden Sonnet ile çalıştı. Üçü de devralan türler listesine girer.
5. **İç içe çağrı ayırt edilebiliyor.** Bir alt ajanın kendi alt ajan çağrısında hook girdisi `agent_id` ve `agent_type` alanlarını taşıyor; ana sohbetin çağrısında bu alanlar yok. İç içe çağrıya dokunulmaz (`agent_id` varsa).
6. **Masaüstü uygulaması:** deneme uygulamanın kendi istemcisiyle yapıldı, ama uygulamanın penceresinden değil. Pencereden yapılan ilk gerçek dağıtım, Mac'te açıldıktan sonra karar kaydından ve alt ajanın kaydından doğrulanacak.
