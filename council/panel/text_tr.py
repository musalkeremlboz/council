"""Every Turkish string the panel shows. The HTML files take them through {{name}} placeholders."""
from council import oauth

TEXTS = {
    "title": "COUNCIL Paneli",
    "brand": "COUNCIL",
    "login_heading": "Giriş",
    "password_label": "Sahip parolası",
    "sign_in": "Giriş yap",
    "wrong_password": "Parola yanlış.",
    "no_owner_password": "Önce sahip parolasını belirle: council set-password",
    "busy": "Veritabanı meşgul, birazdan yeniden dene.",
    "sign_out": "Çıkış yap",
    "nav_label": "Bölümler",
    "nav_schema": "Şema",
    "nav_today": "Bugün",
    "nav_health": "Sağlık",
    "nav_map": "Harita",
    "nav_notes": "Notlar",
    "nav_releases": "Güncellemeler",
}

# The thirteen blocks of the schema. {NAME} placeholders are filled by mechanism.blocks() from the code's own constants.
BLOCKS = {
    "h1": {
        "name": "Hook", "sub": "oturum açıldı",
        "what": "Yardımcı yeni bir oturum açtığında kendiliğinden çalışan küçük betik. Sunucudan başlangıç bağlamını ister ve oturumun önüne koyar.",
        "rules": [
            "Sunucuya 8 saniyede ulaşamazsa oturum hafızasız başlar ve yardımcı bunu sana bir kez söyler.",
            "Oturum sıkıştırıldığında da çalışır.",
            "Hook kullanamayan yardımcılar aynı bağlamı bir araç çağrısıyla alır.",
        ],
    },
    "bas": {
        "name": "Başlangıç bağlamı", "sub": "en çok {START_BUDGET} karakter",
        "what": "Her oturumun başında yüklenen sabit bilgi: kim olduğun, düzeltmelerin, açık konular ve son {START_CARDS} oturumun kartı.",
        "rules": [
            "Toplam bütçe {START_BUDGET} karakter.",
            "Sıra: çekirdek, kurallar, açık konular, oturum kartları.",
            "Sığmayan sessizce atılmaz, adıyla bildirilir.",
        ],
    },
    "diz": {
        "name": "İş tarifi dizini", "sub": "en çok {INDEX_BUDGET} karakter",
        "what": "Kayıtlı iş tariflerinin listesi: tarif başına bir satır, yalnız notun yolu. İstenen iş bir tarifin işiyse yardımcı o notu açar.",
        "rules": [
            "En çok {INDEX_BUDGET} karakter; başlangıç bağlamının bütçesinden ayrıdır.",
            "Önce kalıcı tarifler, sonra adaylar.",
            "Tarifin metni kendiliğinden bağlama girmez.",
        ],
    },
    "h2": {
        "name": "Hook", "sub": "mesaj geldi",
        "what": "Her mesajında çalışır. Mesajı sunucuya gönderir, dönen ilgili notları mesajına ekler.",
        "rules": [
            "Otomatik sistem bildirimleri için arama yapılmaz.",
            "Her mesaja oturum kimliği ve o anki saat eklenir.",
        ],
    },
    "ara": {
        "name": "Arama", "sub": "kelime kökleriyle",
        "what": "Mesajın kelimeleri köklerine indirilir ve bütün notların bölümlerinde aranır.",
        "rules": [
            "Türkçe harfler sadeleştirilir: \"şifre\" ile \"sifre\" aynı sonucu verir.",
            "Dolgu ve istek sözcükleri aramaya girmez.",
            "Kelime tabanlıdır: aynı şeyi başka sözcüklerle sorarsan kaçırabilir.",
        ],
    },
    "sec": {
        "name": "Seçim", "sub": "en çok {MESSAGE_LIMIT} bölüm",
        "what": "Aramanın bulduğu adaylardan mesaja eklenecek olanlar seçilir.",
        "rules": [
            "En çok {MESSAGE_LIMIT} bölüm.",
            "Toplam en çok {MESSAGE_BUDGET} karakter.",
            "Bir bölümden en çok {SECTION_CLIP} karakter alınır.",
            "Kalan yer {MIN_ROOM} karakterin altına inince durur.",
            "Aynı bölüm bir oturumda yalnız bir kez gönderilir.",
        ],
    },
    "isa": {
        "name": "İşaret", "sub": "en çok {SKILL_LIMIT} tarif",
        "what": "Mesajın bir iş tarifiyle kelime olarak eşleşirse o tarifin yolu tek satırlık bir işaret olarak eklenir. Açıp açmamaya yardımcı karar verir.",
        "rules": [
            "Mesaj başına en çok {SKILL_LIMIT} işaret.",
            "Mesajın en az {MIN_HEAD_WORDS} kelimesi tarifin başlığında ya da \"ne zaman\" satırında geçmelidir.",
            "Aynı tarif bir oturumda bir kez işaret edilir.",
        ],
    },
    "h3": {
        "name": "Hook", "sub": "cevap bitti",
        "what": "Yardımcı cevabını bitirirken çalışır. Kaydedilmemiş iş varsa bir kez hatırlatır; uzun bir iş bittiyse öğrenme sorusunu sorar.",
        "rules": [
            "Oturum not ya da dosya değiştirdi ama günlüğe işlemediyse hatırlatır.",
            "Aynı iş için ikinci kez hatırlatmaz.",
            "Yalnız oturum olaylarına bağlanabilen yardımcılarda çalışır.",
        ],
    },
    "yaz": {
        "name": "Yazma", "sub": "kart · konu · günlük",
        "what": "Anlamlı bir iş bitince yardımcı üç şeyi yazar: kendi oturum kartını, ilgili konunun güncel durumunu ve günlük kaydını.",
        "rules": [
            "Bir notu değiştirmeden önce okumak zorunludur; not o arada değiştiyse yazma reddedilir.",
            "Her yazma tarihli bir kayıttır; eski hâl geri getirilebilir.",
            "Her oturum yalnız kendi kartını yazar.",
        ],
    },
    "ogr": {
        "name": "Öğrenme", "sub": "{REVIEW_EVERY} araç çağrısında bir",
        "what": "Uzun bir işin sonunda hafıza yardımcıya sorar: bu işten öğrenilecek bir şey var mı? Düzeltmen kural, işin yolu iş tarifi olur.",
        "rules": [
            "Son sorudan beri en az {REVIEW_EVERY} araç çağrısı yapıldıysa sorulur.",
            "Sır gibi görünen şey yazılamaz.",
            "Yeni tarif aday doğar; {PROMOTE_AFTER} ayrı oturumda işe yararsa kalıcı olur.",
            "{RETIRE_NOT_HELPED} oturum \"işe yaramadı\" deyip hiçbiri \"yaradı\" demediyse ya da {RETIRE_WRONG} kez \"yanlış\" dendiyse emekli olur.",
            "Her öğrenme sana tek satırla bildirilir ve geri alınabilir.",
        ],
    },
    "haf": {
        "name": "Hafıza", "sub": "",
        "what": "Notların kendisi: düz metin dosyaları. Tek doğru kaynak budur; öteki bütün bloklar buradan okur ya da buraya yazar.",
        "rules": [
            "Her değişiklik tarihli bir kayıttır.",
            "İki yardımcı aynı notu birbirinin üstüne yazamaz.",
            "Arama indeksi silinirse notlardan yeniden kurulur.",
        ],
    },
    "yed": {
        "name": "Yedek", "sub": "",
        "what": "Notlar geçmişiyle birlikte özel bir yedek deposuna gönderilir.",
        "rules": [
            "{BACKUP_GRACE_DAYS} gün başarısız kalırsa yardımcı oturum başında seni uyarır.",
            "Denetim soruları da yedeğe girer.",
        ],
    },
    "den": {
        "name": "Denetim", "sub": "",
        "what": "Kayıtlı sorularla hafızanın doğru notu hâlâ bulup bulmadığına bakar. Hiçbir notu değiştirmez.",
        "rules": [
            "Her soru iki yoldan ölçülür: not kendiliğinden geliyor mu, aramayla bulunuyor mu.",
            "Notlar arasındaki kırık bağlantıları da listeler.",
        ],
    },
}


def texts() -> dict:
    """All strings; the lockout rule is built from the sign-in constants every time it is asked for."""
    minutes = -(-oauth.FAILURE_WINDOW // 60)
    return {
        **TEXTS,
        "lockout_rule": f"{oauth.MAX_FAILURES} yanlış denemeden sonra kapı {minutes} dakika kapanır.",
        "locked": f"Çok fazla yanlış deneme. Kapı {minutes} dakika kapalı.",
    }


# The titles, journey steps and live lines of the schema and of today. Values shown beside them are only counts,
# character totals and note paths; nothing here is ever filled with text taken from a note.
KIND_TITLES = {
    "start": "Oturum başladı", "context": "Bağlam istendi", "inject": "Mesaj geldi", "read": "Not okundu",
    "open": "İş tarifi açıldı", "search": "Arama yapıldı", "card": "Oturum kartı yazıldı",
    "thread": "Konu güncellendi", "log": "Günlüğe yazıldı", "note": "Not yazıldı",
    "rule": "Kural öğrenildi", "skill": "İş tarifi öğrenildi",
}

STEPS = {
    "h1": "Oturum açıldı; hook başlangıç bağlamını istedi.",
    "bas": "Başlangıç bağlamı hazırlandı.",
    "diz": "İş tarifi dizini bağlama eklendi.",
    "haf_read": "Hafızadan okundu.",
    "h2": "Mesaj geldi; hook sunucuya gönderdi.",
    "ara": "Mesajın kelimeleri notlarda arandı.",
    "sec": "Eklenecek notlar seçildi.",
    "sec_none": "Mesajla eşleşen not bulunamadı.",
    "isa": "İş tarifi işareti eklendi.",
    "haf_inject": "Seçilen notlar hafızadan okundu.",
    "haf_note": "Bir not okundu.",
    "haf_open": "Bir iş tarifi açıldı.",
    "haf_search": "Arama yapıldı.",
    "h3": "Cevap bitti.",
    "yaz_card": "Oturum kartı yazıldı.",
    "yaz_thread": "Konu güncellendi.",
    "yaz_log": "Günlüğe yazıldı.",
    "yaz_note": "Not yazıldı.",
    "ogr_rule": "Kural öğrenildi.",
    "ogr_skill": "İş tarifi öğrenildi.",
    "haf_written": "Hafızaya tarihli kayıt olarak yazıldı.",
}

VALUES = {
    "notes": "{n} not",
    "chars": "{n} karakter",
    "at_limit": "sınıra dayandı",
    "skills": "{n} tarif",
}

# What each fixed section of the start context is called, and what one unit of it is called.
SECTION_NAMES = {"core.md": "Çekirdek", "rules.md": "Kurallar", "threads.md": "Açık konular",
                 "sessions.md": "Oturum kartları"}
UNIT_NAMES = {"core.md": "çekirdek satırı", "rules.md": "kural satırı", "threads.md": "açık konu",
              "sessions.md": "oturum kartı"}

NUMBERS = {
    "bas_part": "{name}: {chars} karakter gösterildi",
    "bas_left": "{name}: {count} birim sığmadı ({chars} karakter)",
    "diz_listed": "{n} tarif listelendi",
    "diz_left": "{n} tarif dışarıda kaldı",
    "h2_messages": "Son 24 saatte {n} mesaj",
    "sec_given": "{n} mesaja not eklendi",
    "sec_mean": "Not eklenen mesajda ortalama {n} karakter",
    "isa_pointers": "Son 7 günde {n} işaret",
    "isa_opened": "Son 7 günde {n} tarif açıldı",
    "haf_notes": "{n} not",
    "haf_changes": "Son 7 günde {n} değişiklik",
    "yed_ok": "Son başarılı yedek: {when}",
    "yed_none": "Son başarılı yedek: kayıt yok",
    "den_questions": "{n} kayıtlı soru",
}


# The page's own copy: labels, headings and the one-sentence line under every heading. {name} placeholders are
# filled by the page with values from the API (dates, times, counts, block names); a sentence that states a rule
# is built in ui() from the code's own constants.
PAGE = {
    "placeholder": "Bu bölüm henüz hazır değil.",
    "loading": "Yükleniyor…",
    "offline": "bağlantı yok",
    "unavailable": "Bu bölümün verisi şu an okunamadı.",
    "none": "kayıt yok",
    # the schema
    "schema_status": "Mevcut durum",
    "status_backup": "Son yedek",
    "status_backup_failing": "son deneme başarısız",
    "status_notes": "Notlar",
    "status_skills": "İş tarifleri",
    "status_check": "Denetim",
    "status_check_value": "{auto}/{questions} · {search}/{questions}",
    "status_check_note": "kendiliğinden gelen · aramayla bulunan",
    "status_service": "Servis",
    "status_version": "Sürüm",
    "status_version_value": "panel {panel} · servis {service}",
    "status_version_panel": "panel {panel}",
    "status_version_differs": "Panel ve hafıza servisi farklı sürümde çalışıyor; ikisini de yeniden başlat.",
    "service_full": "çalışıyor",
    "service_failed": "yanıt vermiyor",
    "service_none": "kayıt yok",
    "schema_title": "Canlı şema",
    "schema_lede": "Hafıza nasıl çalışıyor? Bir bloğa tıkla: ne yaptığını ve kurallarını gör.",
    "lane_title_start": "Oturum başı",
    "lane_title_message": "Her mesaj",
    "lane_title_end": "İş bitince",
    "lane_reads": "hafızadan okur",
    "lane_writes": "hafızaya yazar",
    "memory_notes": "{n} not",
    "memory_read": "okundu",
    "memory_written": "yazıldı",
    "dot_on": "Akan nokta açık",
    "dot_off": "Akan nokta kapalı",
    "events_title": "Olaylar",
    "events_lede": "Hafızada son ne oldu? Bir olaya tıkla: hangi bloklardan geçtiğini gör.",
    "live_on": "Canlı izleme açık",
    "live_off": "Canlı izlemeyi sürdür",
    "journey": "Olayın yolculuğu",
    "block": "Blok",
    "rules": "Kuralları",
    "numbers": "Şu an",
    "change_block": "Bu bloğun çalışmasını değiştirmek istersen yardımcına bloğun adını söylemen yeter: “{name}”.",
    # today
    "today_title": "Bugün",
    "today_lede": "{date}, 00:00 – {now}. Her daire gerçek bir olay.",
    "today_counts": "Günün sayıları",
    "lane_start": "Oturum başı",
    "lane_inject": "Mesaja not eklendi",
    "lane_read": "Not okundu",
    "lane_search": "Arama",
    "lane_open": "İş tarifi açıldı",
    "lane_pointer": "İşaret gönderildi",
    "strip_title": "Günün olay şeridi",
    "strip_lede": "Bugün ne oldu, ne zaman oldu? Bir daireye tıkla: bütçesi aşağıda görünür.",
    "strip_now": "şimdi",
    "strip_size": "Mesaj dairesinin büyüklüğü eklenen karakter sayısıdır.",
    "strip_selected": "seçili olay",
    "mark_label": "{time} · {lane} · {chars} karakter",
    "at_limit_toggle": "Yalnız sınıra dayananlar · {n}",
    "budget_title": "Bağlam bütçesi",
    "budget_lede": "Yardımcıya ne kadar bilgi verildi, sınırın ne kadarı doldu? Her halka ayrı bir sınırdır.",
    "ring_start": "Oturum başı",
    "ring_selected": "Seçili olay",
    "ring_index": "İş tarifi dizini",
    "ring_label": "{name}: {budget} karakterin {used} karakteri dolu",
    "left_out": "Sığmayan: {list}. Yardımcıya adıyla bildirilir.",
    "left_out_item": "{name} ({chars} karakter)",
    "left_out_none": "Hepsi sığdı.",
    "selected_none": "Bugün mesaj yok.",
    "selected_other": "Bu olay mesaj bütçesini kullanmaz: {chars} karakter.",
    "selected_empty": "Bu mesaja ilgili not bulunamadı.",
    "selected_at_limit": "Sınıra dayandı.",
    "selected_under": "Sınırın altında kaldı.",
    "index_listed": "{n} tarif listelendi",
    "index_left": "{n} tarif dışarıda kaldı.",
    "index_all": "Bütün tarifler sığdı.",
    # health
    "health_title": "Sağlık",
    "health_ok": "Şu an her şey yolunda.",
    "health_attention": "Dikkat isteyen bir şey var.",
    "health_service_full": "Servis çalışıyor.",
    "health_service_failed": "Servis yanıt vermiyor.",
    "health_service_none": "Servisin şu anki durumu için örnek yok.",
    "health_backup_full": "Yedek yolunda.",
    "health_backup_failed": "Yedek başarısız.",
    "health_backup_none": "Yedek kaydı yok.",
    "health_updates_failed": "Kendiliğinden güncelleme sorun bildiriyor.",
    "health_check": "Denetimdeki {questions} sorudan {both} tanesi iki yoldan da bulunuyor.",
    "health_check_none": "Denetim henüz çalışmadı.",
    "history_title": "Sağlık geçmişi",
    "history_lede": "Bir şey bozuldu mu, ne zamandır yolunda? Her işaret bir gün; son 30 gün.",
    "history_empty": "Henüz örnek alınmadı. Panel çalıştıkça günler dolar.",
    "history_today": "bugün",
    "history_first_tick": "ilk kayıt",
    "history_first": "İlk kayıt: {date}. Önceki günlerde panel örnek almadı.",
    "row_service": "Servis",
    "row_service_sub": "hafıza servisi yanıt veriyor mu",
    "row_backup": "Yedek",
    "row_backup_sub": "son yedek başarılı mı",
    "row_updates": "Güncelleme denetimi",
    "row_updates_sub": "kendiliğinden güncelleme sorunsuz mu",
    "day_label": "{date} · {row}: {state}",
    "state_full": "tam",
    "state_partial": "eksik",
    "state_failed": "başarısız",
    "state_none": "kayıt yok",
    "legend_full": "tam: alınan örneklerin hepsi başarılı",
    "legend_partial": "eksik: bir kısmı başarısız",
    "legend_failed": "başarısız: hepsi başarısız",
    "legend_none": "kayıt yok: o gün örnek alınmadı",
    "grid_title": "Arama sağlık ızgarası",
    "grid_lede": "Arama doğru notu buluyor mu, ne zaman bozuldu ya da düzeldi? Her satır kayıtlı bir soru, her sütun denetimin çalıştığı bir an. Soruların metni gösterilmez.",
    "grid_empty": "Denetim henüz çalışmadı ya da kayıtlı soru yok.",
    "grid_auto": "Kendiliğinden geliyor",
    "grid_search": "Aramayla bulunuyor",
    "grid_question": "Soru {n}",
    "grid_total": "{n}/{total}",
    "grid_cell": "Soru {n} · {when} · {group}: {result}",
    "grid_found": "buldu",
    "grid_missed": "kaçırdı",
    "grid_legend_found": "doğru notu buldu",
    "grid_legend_missed": "kaçırdı",
    "grid_legend_gone": "boş hücre: sorunun notu artık yok",
    "grid_legend_missing": "son denetimde kaçan soru",
    "missing_list": "Son denetimde kaçan sorular: {list}.",
    "missing_none": "Son denetimde kaçan soru yok.",
    # notes
    "notes_title": "Notlar",
    "notes_lede": "{n} not. Hangisi işe yarıyor, hangisi hiç çağrılmıyor, hafıza ne zaman değişti?",
    "ranking_title": "Not kullanım sıralaması",
    "ranking_lede": "Hangi not sürekli seçiliyor? Dairenin yeri toplam kullanımdır: mesaja eklenme, yardımcının açıp okuması ve aramada bulunma.",
    "ranking_since": "Kayıt başlangıcı: {date}.",
    "ranking_note": "not",
    "ranking_counts": "eklendi · okundu · bulundu",
    "ranking_row": "{path}: {total} kullanım ({injected} eklendi, {read} okundu, {found} bulundu)",
    "ranking_shown": "İlk {shown} not gösteriliyor; kullanılan not sayısı {n}.",
    "ranking_all": "Kullanılan {n} notun hepsi gösteriliyor.",
    "show_all": "Tümünü göster",
    "show_less": "Daha az göster",
    "always_loaded": "Her oturumun başında kendiliğinden yüklenen notlar ({list}) bu yüzden “eklendi” sayılmaz.",
    "unused_title": "Hiç kullanılmayanlar",
    "unused_count": "{n} / {total}",
    "unused_note": "Kullanılmayan not silinecek demek değildir. İş tarifleri yalnız kendi işleri istendiğinde açılır.",
    "unused_none": "Bütün notlar en az bir kez kullanıldı.",
    "pulse_title": "Hafıza nabzı",
    "pulse_lede": "Hafıza hangi günlerde ne kadar değişti? Dairenin büyüklüğü o günkü değişiklik sayısıdır. Bir güne tıkla.",
    "pulse_sum": "son {days} gün · {changes} değişiklik · {added} yeni not",
    "pulse_before": "kayıt yok",
    "pulse_quiet": "değişiklik yok",
    "pulse_step": "{from}–{to}",
    "pulse_step_last": "{from} ve üstü değişiklik",
    "pulse_day": "{date} {weekday}",
    "pulse_day_label": "{date} {weekday}: {changes} değişiklik",
    "pulse_counts": "{changes} değişiklik · {notes} not değişti · {added} yeni not",
    "weekdays_short": ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"],
    "weekdays": ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"],
    # the map
    "map_title": "Hafıza haritası",
    "map_lede": "Her nokta bir not, her çizgi iki not arasındaki bağlantı. Notların metni gösterilmez, yalnız adları.",
    "map_label": "Hafıza haritası: {notes} not, {links} bağlantı",
    "map_sum": "{notes} not · {links} bağlantı · {regions} bölge",
    "regions_title": "Bölgeler",
    "regions_all": "Hepsini göster",
    "names_on": "Adlar",
    "names_hidden": "Adlar ({n} notun üstünde kapalı)",
    "turn_on": "Döndür",
    "turn_left": "Sola çevir",
    "turn_right": "Sağa çevir",
    "zoom_in": "Yaklaş",
    "zoom_out": "Uzaklaş",
    "map_hint": "SÜRÜKLE: çevir · KAYDIR: yaklaş · TIKLA: notu seç",
    "legend_note": "not",
    "legend_skill": "iş tarifi",
    "legend_core": "her oturumda yüklenen notlar",
    "legend_recent": "son mesajın notları",
    "pick_label": "Not seç",
    "pick_none": "—",
    "selected_note": "Seçili not · {region}",
    "note_sections": "{n} bölüm",
    "note_chars": "{n} karakter",
    "note_links": "{n} bağlantı",
    "note_changed": "son değişiklik {date}",
    "note_recent": "son mesaja eklendi",
    "neighbours": "Bağlı olduğu notlar",
    "neighbours_none": "Bu notun bağlantısı yok.",
    "map_empty_card": "Bir noktaya tıkla ya da listeden bir not seç: notun yolunu, bölgesini ve hangi notlara bağlı olduğunu gör.",
    # releases
    "releases_title": "Güncellemeler",
    "ring_title": "Halka",
    "ring_lede": "Halkanın her parçası sistemin temel bir özelliğidir. Bir özellik testlerini ve ölçümlerini geçtiğinde parçası dolar.",
    "ring_count": "{n} / {total}",
    "ring_count_label": "parça dolu",
    "ring_aria": "Halka: {total} parçanın {n} parçası dolu",
    "ring_part": "{n} · {name}",
    "ring_parts": "{from} – {to}",
    "ring_full": "dolu",
    "ring_measured": "yazıldı, ölçülüyor",
    "ring_waiting": "bekliyor",
    "ring_unnamed": "adı bekliyor",
    "versions_title": "Sürümler",
    "state_pending": "Yayın bekliyor",
    "state_released": "Yayınlandı",
    "state_first": "İlk sürüm",
    "next_title": "Sıradakiler",
}


def ui() -> dict:
    """The page's copy, with every sentence that carries a number built from the constants at call time."""
    from council import context
    from council.panel import sampler
    from council.panel.mechanism import _number

    return {
        **PAGE,
        "history_rule": (f"Panel {sampler.SAMPLE_EVERY // 60} dakikada bir bakar; günün durumu o günkü "
                         "örneklerden çıkar."),
        "grid_rule": (f"Denetim notlar değiştiğinde, değişmezse {sampler.CHECK_EVERY // 60} dakikada bir "
                      "çalışır; son çalıştırmalar gösterilir."),
        "at_limit_definition": (
            f"Sınıra dayanan mesaj: eklenen toplam karakter, {_number(context.MESSAGE_BUDGET)} karakterlik mesaj "
            f"bütçesinin son {_number(context.MIN_ROOM)} karakterine girmiştir. Kayıt bir bölümün kırpıldığını "
            "ya da dışarıda kaldığını tutmaz; panel bunu iddia etmez."),
    }


# The folders of the vault the map names; any other folder is shown under its own name.
REGIONS = {"cekirdek": "Çekirdek", "gecmis": "Geçmiş", "knowledge": "Bilgi", "skills": "İş tarifleri",
           "imported": "İçe aktarılan"}
