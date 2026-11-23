# COUNCIL kurulum rehberi

[English](setup.md) · [Ana sayfa](../README.md)

İki kullanım biçimi var. Çoğu kişiye birincisi yeter.

| | Kimler bağlanabilir | Ne gerekir |
|---|---|---|
| **[Bu bilgisayar](#bilgisayar)** | Bu bilgisayardaki yardımcılar | Python 3.11+, git |
| **[Kendi sunucun](#sunucu)** | Bütün cihazların, claude.ai ve telefon dahil | Alan adı olan bir Linux sunucu |

<a id="bilgisayar"></a>
## 1. Bu bilgisayara kur

**En kolay yol, kurulumu yardımcına yaptırmaktır.** Şu cümleyi yapay zekâ yardımcına yapıştır:

```text
Şu yönergeyi oku ve COUNCIL'i kur:
https://raw.githubusercontent.com/musalkeremlboz/council/main/INSTALL.md
```

Yardımcın [INSTALL.md](../INSTALL.md) dosyasını okur ve aşağıdaki adımları senin yerine uygular. Kendin kurmak istersen:

**macOS ve Linux**

```sh
curl -fsSL https://raw.githubusercontent.com/musalkeremlboz/council/main/install.sh | sh
```

**Windows** (PowerShell)

```powershell
irm https://raw.githubusercontent.com/musalkeremlboz/council/main/install.ps1 | iex
```

Kurulum yönetici yetkisi istemez ve dört iş yapar:

1. **Hafıza.** COUNCIL'i `~/.council` klasörüne, kendi Python ortamıyla kurar. Notların `~/.council/vault/` klasöründe durur. Bilgisayarında var olan yardımcı hafızasını içeri alır ([ayrıntı](#aktarim)).
2. **Servis.** Hafıza servisini `127.0.0.1:8765` adresinde başlatır. Servis oturum açtığında kendiliğinden çalışır ve yalnız bu bilgisayardan erişilir.
3. **Claude Code.** Hook'ları (Claude Code'un belirli anlarda kendiliğinden çalıştırdığı küçük betikler) ve MCP araçlarını bağlar. `~/.claude/settings.json` ve `~/.claude.json` dosyalarındaki öteki ayarlarını korur. Değiştirmeden önce `.before-council` uzantılı birer yedek alır.
4. **Güncelleme.** Günlük güncelleme denetimini açar ([ayrıntı](#guncelleme)).

Bittiğinde yeni bir Claude Code oturumu aç.

### Seçenekler

Seçenekler komutun sonuna `sh -s --` ile eklenir:

```sh
curl -fsSL https://raw.githubusercontent.com/musalkeremlboz/council/main/install.sh | sh -s -- --no-auto-update
```

| Seçenek | Ne yapar |
|---|---|
| `--no-auto-update` | Otomatik güncellemeyi kapatır |
| `--no-import` | Var olan hafızayı aramaz |
| `--from KLASÖR` | Bulunanlar yerine bu klasörü içe alır |
| `--port 8765` | Servisin dinlediği kapıyı değiştirir |
| `--force` | Bu bilgisayar başka bir COUNCIL hafızasına bağlıysa bağlantıyı yerel hafızaya çevirir |

Bu bilgisayar zaten başka bir COUNCIL hafızasına bağlıysa kurulum hiçbir şeyi değiştirmeden durur ve bunu söyler.

### Doğrula

```sh
~/.council/venv/bin/council status
```

Windows'ta komut `%USERPROFILE%\.council\venv\Scripts\council.exe` yolundadır.

```text
version      0.2.1
service      running on http://127.0.0.1:8765 (0.2.1)
hooks        installed
auto-update  on
notes        /Users/sen/.council/vault
```

### Kaldır

```sh
~/.council/venv/bin/council uninstall
```

Servisi, güncelleme denetimini, hook'ları ve MCP bağlantısını kaldırır. Başka araçların ayarlarına dokunmaz. Notların `~/.council/vault/` klasöründe kalır.

<a id="aktarim"></a>
## 2. Var olan hafızanın aktarımı

Hiçbir hafıza sistemi listesi tam olamayacağı için aktarım iki katmanlıdır.

**Kurulum sırasında, dosyalardan tanınanlar kopyalanır:**

| Kaynak | Nereden okunur | Nereye gider |
|---|---|---|
| Claude Code | `~/.claude/CLAUDE.md`, `~/.claude/projects/*/memory/*.md` | `imported/claude-code/` |
| Codex | `~/.codex/AGENTS.md`, `~/.codex/memories/` | `imported/codex/` |
| Gemini | `~/.gemini/GEMINI.md` | `imported/gemini/` |
| Düzeni tanınan not kasaları | Claude Code'da açtığın klasörler | Doğrudan `core.md`, `rules.md`, `threads.md` ve proje notlarına |

`imported/` altındaki notlar aranabilir, ama her oturumda yüklenmez. Bir not kasası yalnız hafıza henüz boşken doğrudan yerleştirilir; kullanılan bir hafızanın üstüne yazılmaz.

**İlk oturumda, gerisini yardımcın tamamlar.** Kurulum hafızaya bir görev bırakır. Yardımcın:

1. Bu bilgisayarda başka bir hafıza sistemi kullanılıp kullanılmadığına bakar: not klasörleri, yönerge dosyaları, hafıza MCP sunucuları, bağlam ekleyen hook'lar. Varsa okur ve hâlâ geçerli olanı taşır.
2. `imported/` altındakileri yerlerine dağıtır: kalıcı bilgiler ve tercihler `core.md` dosyasına, düzeltmeler `rules.md` dosyasına, proje bilgisi `projects/<ad>/` altına.
3. Neyi taşıdığını sana söyler ve görevi kapatır.

Kaynak dosyalar hiçbir adımda değiştirilmez ya da silinmez. Aynı kaynak ikinci kez içe alınmaz.

Sonradan bir klasörü içe almak için:

```sh
council import ~/Belgeler/Notlarım    # bir not klasörü
council import                         # bu bilgisayarda bulunan her şey
```

<a id="guncelleme"></a>
## 3. Otomatik güncelleme

Günde bir kez bu deponun yayınlanmış son sürümüne bakılır. Yenisi varsa:

1. Yeni sürüm COUNCIL'in kendi Python ortamına kurulur.
2. Hook betiği yenilenir, servis yeniden başlatılır.
3. Yardımcın bir sonraki oturumda sürümün değiştiğini sana söyler.

Notlarına dokunulmaz. Yalnız yayınlanmış sürümler kurulur, depodaki ara değişiklikler kurulmaz. Güncelleme arka arkaya başarısız olursa yardımcın bunu da bildirir.

| | |
|---|---|
| Hemen güncelle | `council update` |
| Durumu gör | `council status` |
| Kapat | `council install --no-auto-update` |
| Yeniden aç | `council install` |

Otomatik güncelleme, bu depoyu yayınlayanın bilgisayarında kod çalıştırmasına izin vermek demektir. Bunu istemiyorsan kapat ve sürümleri kendin gözden geçir.

<a id="sunucu"></a>
## 4. Kendi sunucuna kur

Telefonunu, claude.ai'yi ve birden çok bilgisayarı aynı hafızaya bağlamak için hafızanın internetten erişilen bir adreste durması gerekir. Komutlar Debian ya da Ubuntu içindir ve yönetici yetkisi ister.

```sh
sudo mkdir -p /opt/council /var/lib/council
sudo python3 -m venv /opt/council/.venv
sudo /opt/council/.venv/bin/pip install git+https://github.com/musalkeremlboz/council
sudo COUNCIL_DATA=/var/lib/council /opt/council/.venv/bin/council token
sudo COUNCIL_DATA=/var/lib/council /opt/council/.venv/bin/council set-password --generate
```

Dördüncü komut erişim anahtarını, beşincisi sahip şifresini bir kez gösterir. İkisini de güvenli bir yere yaz.

**Servis.** [`deploy/council.service`](../deploy/council.service) dosyasını `/etc/systemd/system/` altına kopyala. İçindeki `memory.example.com` yerine kendi alan adını, `Europe/Istanbul` yerine kendi saat dilimini yaz. Sonra:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now council
```

**HTTPS.** Alan adının A kaydını sunucunun adresine yönlendir. [Caddy](https://caddyserver.com) kur, [`deploy/Caddyfile`](../deploy/Caddyfile) içeriğini alan adınla birlikte `/etc/caddy/Caddyfile` dosyasına yaz ve `sudo systemctl reload caddy` çalıştır. Caddy sertifikayı kendisi alır.

Servis yalnız `127.0.0.1` adresini dinler. Dışarıya açılan tek kapı Caddy'dir. `curl https://alan-adin/health` komutu `{"ok":true,...}` yazmalı.

**Notları taşı.** Bilgisayarında bir hafıza varsa `~/.council/vault/` klasörünü sunucuda `/var/lib/council/vault/` olarak kopyala ve `council reindex` çalıştır.

### Bilgisayarlarını sunucuya bağla

Claude Code kullandığın her bilgisayarda:

**Ayar dosyası.** `~/.config/council/config.json`:

```json
{"url": "https://alan-adin", "token": "ANAHTARIN", "timezone": "Europe/Istanbul"}
```

`timezone` isteğe bağlıdır. Notlara yazılan saatin, saat dilimi farklı bir makinede de doğru çıkmasını sağlar.

**Hook betiği.**

```sh
mkdir -p ~/.council
curl -fsSL https://raw.githubusercontent.com/musalkeremlboz/council/main/council/hook.py -o ~/.council/hook.py
chmod 600 ~/.config/council/config.json
```

**Hook kaydı.** `~/.claude/settings.json` dosyasındaki `hooks` bölümüne şunları ekle. Dosyada başka hook'lar varsa onları silme, yanlarına ekle.

```json
{
  "hooks": {
    "SessionStart": [
      {"hooks": [{"type": "command", "command": "python3 ~/.council/hook.py", "timeout": 10}]}
    ],
    "UserPromptSubmit": [
      {"hooks": [{"type": "command", "command": "python3 ~/.council/hook.py", "timeout": 8}]}
    ],
    "Stop": [
      {"hooks": [{"type": "command", "command": "python3 ~/.council/hook.py", "timeout": 5}]}
    ]
  }
}
```

| Hook | Ne zaman çalışır | Ne yapar |
|---|---|---|
| `SessionStart` | Oturum açılınca | Başlangıç bağlamını yükler |
| `UserPromptSubmit` | Her mesajında | Mesajla ilgili notları ekler |
| `Stop` | Yardımcı cevabını bitirince | Kaydedilmemiş iş varsa bir kez hatırlatır |

**MCP araçları.**

```sh
claude mcp add --scope user --transport http council https://alan-adin/mcp \
  --header "Authorization: Bearer ANAHTARIN"
```

**Doğrula.**

```sh
echo '{"hook_event_name":"SessionStart","session_id":"deneme"}' | python3 ~/.council/hook.py
```

Çıktıda `COUNCIL session=deneme` ile başlayan bir bağlam görünmeli.

### claude.ai'yi ve telefonu bağla

1. claude.ai'de Ayarlar → Bağlayıcılar → Özel bağlayıcı ekle.
2. Adres olarak `https://alan-adin/mcp` yaz. Gelişmiş ayarları boş bırak.
3. Bağlan'a basınca COUNCIL'in giriş sayfası açılır. Sahip şifresini gir ve onayla.

Bağlayıcı aynı hesapla açtığın masaüstü ve telefon uygulamalarında da görünür. Bu yardımcılarda hook yoktur; hafızayı oturum başında bir araç çağrısıyla kendileri yükler.

### Yedeği kur

Notların zaten bir git deposudur. Yedek, bu depoyu senin özel bir uzak depona gönderir.

1. GitHub'da ya da başka bir git sunucusunda **özel** bir depo aç. İçinde kişisel hafızan duracak.
2. Sunucunun bu depoya yazabilmesi için bir SSH anahtarı tanımla.
3. Uzak depoyu `backup` adıyla ekle ve dene:

```sh
git -C /var/lib/council/vault remote add backup git@github.com:HESABIN/DEPON.git
sudo COUNCIL_DATA=/var/lib/council /opt/council/.venv/bin/council backup
```

`backup ok` yazmalı. Düzenli yedek için [`deploy/council-backup.service`](../deploy/council-backup.service) ve [`deploy/council-backup.timer`](../deploy/council-backup.timer) dosyalarını `/etc/systemd/system/` altına kopyala:

```sh
sudo systemctl enable --now council-backup.timer
```

Zamanlayıcı 15 dakikada bir çalışır. Yedek iki gün başarısız kalırsa yardımcın oturum başında seni uyarır. Yedeğe notlar ve `council check` için kaydettiğin sorular girer (soruların kopyası `vault/.council/` altında tutulur; orası not değildir, aranmaz). Erişim anahtarı, sahip şifresi ve giriş kayıtları `vault/` klasörünün dışında durur ve yedeğe girmez.

Aynı yedek kendi bilgisayarındaki hafıza için de kurulabilir: uzak depoyu `~/.council/vault` içine ekle ve `council backup` komutunu çalıştır.

### Paneli kur

Panel, hafızanın nasıl çalıştığını tarayıcıdan izlemene yarar. Şunları gösterir: hafızanın işleyişini canlı bloklar olarak, bugünün olaylarını, sağlık durumunu, notların haritasını, notların kullanımını ve sürümleri. Not yollarını, sayıları ve saatleri gösterir; not metnini hiçbir yerde göstermez.

Panel hafızayı yalnız okur. Yazdığı tek dosya veri klasöründeki `panel.sqlite3` dosyasıdır: oturumlar, yanlış girişler, sağlık örnekleri ve denetim sonuçları (soru metni yok) orada durur.

Girmek için sahip şifresi gerekir (`council set-password`, bkz. yukarıdaki kurulum). Beş yanlış şifre girişi 15 dakika kilitler. Bu kilit giriş sayfasına ulaşabilen herkes için ortaktır: başkasının yanlış denemeleri seni de 15 dakikalığına dışarıda bırakabilir. Hafıza servisinin kendi giriş sayfasında da durum aynıdır. Biri yanlış şifre denemeyi sürdürdükçe kilit kapalı kalır; o sırada zaten girmiş oturumlar çalışmaya devam eder.

Oturumlar `panel.sqlite3` dosyasında durur; bu yüzden şifreyi değiştirmek de panel servisini yeniden başlatmak da açık oturumları bitirmez. Bir oturum, çıkış yapınca ya da girişten 12 saat sonra biter. Hepsini hemen bitirmek için panel servisini durdur, `panel.sqlite3` dosyasını sil (sağlık geçmişi ve denetim sonuçları da silinir) ve servisi yeniden başlat.

Elle çalıştırmak için:

```sh
sudo COUNCIL_DATA=/var/lib/council /opt/council/.venv/bin/council panel
```

| Seçenek | Varsayılan | Ne yapar |
|---|---|---|
| `--host` | `127.0.0.1` | Panelin dinlediği adres |
| `--port` | `8766` | Panelin portu |
| `--base-path` | `/panel` | Panelin adresteki yolu |
| `--service-url` | `http://127.0.0.1:8765` | Sağlık örneği için hafıza servisinin adresi |

Sürekli çalışması için [`deploy/council-panel.service`](../deploy/council-panel.service) dosyasını `/etc/systemd/system/` altına kopyala:

```sh
sudo systemctl enable --now council-panel.service
```

Sonra [`deploy/Caddyfile`](../deploy/Caddyfile) içindeki satırları kendi Caddy ayarına ekle: tam olarak `/panel` ve `/panel/` ile başlayan yollar panele gider (`/panelx` gitmez), geri kalan her şey hafıza servisine.

```
@panel path /panel /panel/*
handle @panel {
	reverse_proxy 127.0.0.1:8766
}
handle {
	reverse_proxy 127.0.0.1:8765
}
```

Panelin adresi `https://alan-adin/panel/` olur. Bir vekil sunucunun arkasında `Host` başlığı panele değişmeden ulaşmalıdır (Caddy'nin `reverse_proxy` komutu bunu kendiliğinden yapar). `Host` başlığını değiştiren bir vekil girişin 403 vermesine yol açar; çünkü panel isteğin Origin başlığını Host başlığıyla karşılaştırır.

## 5. Komutlar

| Komut | Ne yapar |
|---|---|
| `council install` | Bu bilgisayara kurar: servis, Claude Code, içe aktarma, güncelleme |
| `council status` | Servis çalışıyor mu, hook'lar ve güncelleme açık mı |
| `council update` | Yayınlanmış son sürüm daha yeniyse kurar |
| `council uninstall` | Servisi ve bağlantıları kaldırır, notlara dokunmaz |
| `council import [KLASÖR]` | Bir not klasörünü ya da bulunan her şeyi içe alır |
| `council serve` | Servisi elle çalıştırır |
| `council token` | Erişim anahtarını gösterir; `--rotate` yenisini üretir |
| `council set-password` | Sahip şifresini belirler; `--generate` rastgele üretir |
| `council context "soru"` | Yardımcının göreceği bağlamı yazdırır |
| `council search "kelime"` | Notlarda arar; hiçbir notta geçmeyen sözcükleri de söyler |
| `council check` | Kayıtlı soruların notlarını hâlâ bulup bulmadığına ve notlar arası kırık bağlantılara bakar; hiçbir notu değiştirmez |
| `council check add "soru" NOT` | Bir soruyu ve getirmesi beklenen notu kaydeder (`remove "soru"` çıkarır) |
| `council reindex` | Arama indeksini notlardan yeniden kurar |
| `council usage --days 7` | Hafızanın son günlerde neyi verdiğini özetler |
| `council backup` | Notları `backup` adlı uzak depoya gönderir |
| `council panel` | Salt okunur izleme panelini çalıştırır (`--host`, `--port`, `--base-path`, `--service-url`) |

Veri klasörü varsayılan olarak `~/.council` olur. Başka bir klasör için `--data KLASÖR` ya da `COUNCIL_DATA`.

## Sorun giderme

| Belirti | Neden ve çözüm |
|---|---|
| Kurulum "Python 3.11 or later is needed" diyor | Bilgisayardaki Python eski. [python.org](https://www.python.org/downloads/) adresinden yenisini kur. |
| Kurulum "already connected to a COUNCIL memory" diyor | Bu bilgisayar başka bir hafızaya bağlı. Yerel hafızaya çevirmek için `council install --force`. |
| `council status` "not running" diyor | `~/.council/service.log` dosyasına bak. Yeniden kurmak için `council install`. |
| Hook `COUNCIL memory is unreachable` diyor | Servis kapalı ya da `config.json` içindeki adres yanlış. `council status` ile dene. |
| Linux'ta "systemd user services are not available" | Bu oturumda kullanıcı servisleri çalışmıyor. `council serve` komutunu elle çalıştır. |
| `401` ya da `unauthorized` | Anahtar yanlış. `council token` çıktısıyla `config.json` içindekini karşılaştır. |
| claude.ai giriş sayfası "Too many wrong attempts" diyor | Beş yanlış şifre denemesi girişi 15 dakika kilitler. Bekle ve yeniden dene. |
| Arama boş dönüyor | `council reindex` indeksi yeniden kurar. |
| Komut `no memory at KLASÖR` diyor | O klasörde hafıza yok: `--data` ya da `COUNCIL_DATA` yanlış, ya da bu bilgisayar bir sunucudaki hafızaya bağlı ve notlar orada. Komutu hafızanın durduğu yerde çalıştır. |
