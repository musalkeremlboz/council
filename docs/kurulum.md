# COUNCIL kurulum rehberi

[English](setup.md) · [Ana sayfa](../README.md)

Bu rehberi bir insan da bir yapay zekâ yardımcısı da izleyebilir.

> **Yardımcıysan:** adımları sırayla uygula ve her bölümün sonundaki doğrulamayı çalıştır. Erişim anahtarını ve sahip şifresini sohbete yazma; dosyaya yaz, kullanıcıya yerini söyle. Var olan bir ayar dosyasını değiştirmeden önce yedeğini al ve içindeki öteki ayarları koru.

## 0. Gerekenler

- Python 3.11 ya da üstü
- git
- Birden çok cihazdan bağlanmak için: alan adı olan, sürekli açık bir Linux sunucu

İki kurulum biçimi var. Hangisini seçersen seç, sonradan öbürüne geçmek için `vault/` klasörünü kopyalaman yeter.

| | Kimler bağlanabilir | Ne gerekir |
|---|---|---|
| **A. Tek bilgisayar** | Yalnız o bilgisayardaki yardımcılar | Hiçbir şey |
| **B. Sunucu** | Bütün cihazların, claude.ai ve telefon dahil | Linux sunucu ve alan adı |

## 1. Sunucuyu kur

### A. Tek bilgisayar

```sh
python3 -m venv ~/.council/venv
~/.council/venv/bin/pip install git+https://github.com/musalkeremlboz/council
~/.council/venv/bin/council token
```

Son komut erişim anahtarını üretir ve gösterir. Anahtar `~/.council/token` dosyasında durur; notların `~/.council/vault/` klasöründedir. Başka bir klasör istersen `COUNCIL_DATA` ortam değişkenini ayarla.

Servisi başlat:

```sh
nohup ~/.council/venv/bin/council serve > ~/.council/serve.log 2>&1 &
```

Servis `127.0.0.1:8765` adresinde çalışır ve bilgisayar yeniden başlayınca kapanır; o zaman aynı komutu yeniden çalıştır.

### B. Sunucu

Komutlar Debian ya da Ubuntu içindir ve yönetici yetkisi ister.

```sh
sudo mkdir -p /opt/council /var/lib/council
sudo python3 -m venv /opt/council/.venv
sudo /opt/council/.venv/bin/pip install git+https://github.com/musalkeremlboz/council
sudo COUNCIL_DATA=/var/lib/council /opt/council/.venv/bin/council token
sudo COUNCIL_DATA=/var/lib/council /opt/council/.venv/bin/council set-password --generate
```

Son komut sahip şifresini bir kez gösterir. claude.ai'yi bağlarken bu şifre sorulur; güvenli bir yere yaz.

**Servis.** [`deploy/council.service`](../deploy/council.service) dosyasını `/etc/systemd/system/` altına kopyala. İçindeki `memory.example.com` yerine kendi alan adını, `Europe/Istanbul` yerine kendi saat dilimini yaz. Sonra:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now council
```

**HTTPS.** Alan adının A kaydını sunucunun adresine yönlendir. [Caddy](https://caddyserver.com) kur, [`deploy/Caddyfile`](../deploy/Caddyfile) içeriğini alan adınla birlikte `/etc/caddy/Caddyfile` dosyasına yaz ve `sudo systemctl reload caddy` çalıştır. Caddy sertifikayı kendisi alır.

Servis yalnız `127.0.0.1` adresini dinler. Dışarıya açılan tek kapı Caddy'dir.

### Doğrula

```sh
curl http://127.0.0.1:8765/health
```

`{"ok":true,"version":"0.1.0"}` yazmalı. Sunucu kurulumunda ayrıca `curl https://alan-adin/health` aynı cevabı vermeli.

<a id="claude-code"></a>
## 2. Claude Code'u bağla

Bu bölümü Claude Code kullandığın her bilgisayarda uygula. `ADRES`, tek bilgisayar kurulumunda `http://127.0.0.1:8765`, sunucu kurulumunda `https://alan-adin` olur.

**Ayar dosyası.** `~/.config/council/config.json`:

```json
{"url": "ADRES", "token": "ANAHTARIN", "timezone": "Europe/Istanbul"}
```

```sh
chmod 600 ~/.config/council/config.json
```

`timezone` isteğe bağlıdır. Notlara yazılan saatin, saat dilimi farklı bir makinede de doğru çıkmasını sağlar.

**Hook betiği.** Hook, Claude Code'un belirli anlarda kendiliğinden çalıştırdığı küçük betiktir. Yalnız Python'ın standart kitaplığını kullanır, ayrıca bir şey kurmak gerekmez.

```sh
mkdir -p ~/.council
curl -fsSL https://raw.githubusercontent.com/musalkeremlboz/council/main/council/hook.py -o ~/.council/hook.py
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

**MCP araçları.** Yardımcının hafızada arama yapıp not yazabilmesi için:

```sh
claude mcp add --scope user --transport http council ADRES/mcp \
  --header "Authorization: Bearer ANAHTARIN"
```

### Doğrula

```sh
echo '{"hook_event_name":"SessionStart","session_id":"deneme"}' | python3 ~/.council/hook.py
```

Çıktıda `COUNCIL session=deneme` ile başlayan bir bağlam görünmeli. `COUNCIL memory is unreachable` yazıyorsa adres ya da anahtar yanlıştır ya da servis çalışmıyordur.

Sonra yeni bir Claude Code oturumu aç ve "Hafızanda ne var?" diye sor.

## 3. claude.ai'yi ve telefonu bağla

Yalnız sunucu kurulumunda yapılabilir.

1. claude.ai'de Ayarlar → Bağlayıcılar → Özel bağlayıcı ekle.
2. Adres olarak `https://alan-adin/mcp` yaz. Gelişmiş ayarları boş bırak.
3. Bağlan'a basınca COUNCIL'in giriş sayfası açılır. Sahip şifresini gir ve onayla.

Bağlayıcı aynı hesapla açtığın masaüstü ve telefon uygulamalarında da görünür. Bu yardımcılarda hook yoktur; hafızayı oturum başında bir araç çağrısıyla kendileri yükler.

## 4. Yedeği kur

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

Zamanlayıcı 15 dakikada bir çalışır. Yedek iki gün başarısız kalırsa yardımcın oturum başında seni uyarır.

Yedeğe yalnız notlar girer. Erişim anahtarı, sahip şifresi ve giriş kayıtları `vault/` klasörünün dışında durur.

## 5. Komutlar

| Komut | Ne yapar |
|---|---|
| `council serve` | Servisi çalıştırır |
| `council token` | Erişim anahtarını gösterir; `--rotate` yenisini üretir |
| `council set-password` | Sahip şifresini belirler; `--generate` rastgele üretir |
| `council context "soru"` | Yardımcının göreceği bağlamı yazdırır |
| `council search "kelime"` | Notlarda arar |
| `council reindex` | Arama indeksini notlardan yeniden kurar |
| `council usage --days 7` | Hafızanın son günlerde neyi verdiğini özetler |
| `council backup` | Notları `backup` adlı uzak depoya gönderir |
| `council import-avenox KLASÖR` | Avenox Beyin V3 kasasını içe aktarır |

Veri klasörü varsayılan olarak `~/.council` olur. Başka bir klasör için `--data KLASÖR` ya da `COUNCIL_DATA`.

## 6. Güncelleme

```sh
sudo /opt/council/.venv/bin/pip install -U git+https://github.com/musalkeremlboz/council
sudo systemctl restart council
```

Tek bilgisayar kurulumunda `~/.council/venv/bin/pip` ile aynı komutu çalıştır, servisi durdurup yeniden başlat. Hook betiği değiştiyse 2. bölümdeki `curl` komutunu yinele. Notlarına dokunulmaz.

## Sorun giderme

| Belirti | Neden ve çözüm |
|---|---|
| `no token: run council token first` | Servis anahtarı bulamadı. `council token` komutunu servisle aynı veri klasörüyle çalıştır. |
| Hook `COUNCIL memory is unreachable` diyor | Servis kapalı ya da `config.json` içindeki adres yanlış. `curl ADRES/health` ile dene. |
| `401` ya da `unauthorized` | Anahtar yanlış. `council token` çıktısıyla `config.json` içindekini karşılaştır. |
| claude.ai giriş sayfası "Too many wrong attempts" diyor | Beş yanlış şifre denemesi girişi 15 dakika kilitler. Bekle ve yeniden dene. |
| Arama boş dönüyor | `council reindex` indeksi yeniden kurar. |
