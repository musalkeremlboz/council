// Çizgi ve söz (sahne). Logonun iki biçimi: çizgi asıl çizimdir; söz aynı geometri, Council Halka harfleriyle.
// Bölüm ilk görününce bir kez 45° kesikli geçişle söze geçer, yaklaşık altı saniye kalır, çizgiye döner ve durur.
// İki Tek Kesik düğmesiyle biçim elle seçilir; elle seçince tur biter. Kor O iki biçimde de aynıdır: yalnız ilk
// biçimden çizilir ve geçişte hiç kesilmez. JS yoksa ya da hareket azaltılmışsa iki biçim yan yana (telefonda alt alta).
//
// İşaretleme (amblemSvg() çıktısı durağan olarak sayfaya yazılır):
//   <div class="s-cs">
//     <figure class="s-cs__bicim" data-bicim="cizgi">
//       <div class="s-cs__amblem" role="img" aria-label="COUNCIL logosu, çizgi biçimi">amblemSvg("cizgi", "cs-cizgi")</div>
//       <figcaption>…</figcaption></figure>
//     <figure class="s-cs__bicim" data-bicim="soz"> … amblemSvg("soz", "cs-soz") … </figure>
//   </div>
//   <div class="s-cs__secici" role="group" aria-label="Logonun biçimi" hidden>
//     <button type="button" class="c-dugme c-dugme--k" data-bicim="cizgi" aria-pressed="true">Çizgi</button>
//     <button type="button" class="c-dugme c-dugme--k c-dugme--ikincil" data-bicim="soz" aria-pressed="false">Söz</button>
//   </div>
// baslat(bolum) ikisini de içeren bölümü alır.

import { hareketAzaltildi, azaltmaIzle, gorunurlukBekcisi, kokuIsaretle } from "./ortak.js";

export const TUR = [{ id: "soz", bekle: 1200 }, { id: "cizgi", bekle: 6800 }];
export const GECIS = { duration: 840, easing: "cubic-bezier(.2,0,0,1)", fill: "forwards" };
// Söz biçiminin sözleri (Türkçe); öteki diller brand/js/metin.json'dan (cizgiSoz) gelir. Yerleşim: söz yolda kaç kez
// tekrarlanır ve harf aralığı (px); sözün boyu dile göre değiştiği için yazı yolu tam doldursun diye ölçülüp yazılır.
export const SOZ = {
  c: "BİRÇOK ÜYE · TEK HAFIZA", ci: "TEK HAFIZA · BİRÇOK ÜYE", dalga: "ORTAK HAFIZA",
  yerlesim: { c: { tekrar: 3, ara: 1.08 }, ci: { tekrar: 3, ara: 0.08 }, dalga: { tekrar: 2, ara: 2.49 } },
};

const DALGA = "M-56 0A56 56 0 0 1 56 0A56 56 0 0 0 168 0";
const C_YOL = "M168 0A168 168 0 1 1 0 -168";
const SVG = 'viewBox="0 0 400 400" aria-hidden="true" focusable="false"';
const tekrar = (metin, k) => Array(k).fill(metin).join(" · ");

// Bir biçimin amblemi: kor O (aynı) + biçimin kendi C'si ve dalgası.
export function amblemSvg(bicim, uid, soz = SOZ) {
  const kor = `<svg class="s-cs__kor" ${SVG}><defs><mask id="${uid}" maskUnits="userSpaceOnUse" x="0" y="0" width="400" height="400">` +
    `<rect width="400" height="400" fill="white"/><path transform="translate(200 200)" d="${DALGA}" fill="none" stroke="black" stroke-width="48"/>` +
    `</mask></defs><circle class="s-kor" cx="200" cy="200" r="112" fill="none" stroke-width="28" mask="url(#${uid})"/></svg>`;
  if (bicim !== "soz") {
    return kor + `<svg class="s-cs__form" ${SVG}><g fill="none" stroke="currentColor" stroke-width="28">` +
      `<path transform="translate(200 200) rotate(45)" d="${C_YOL}"/><path transform="translate(200 200)" d="${DALGA}"/></g></svg>`;
  }
  // C iki satır (dış ve iç yarıçap), dalga iki satır: harflerin orta çizgisi çizgi biçiminin kalınlığı içinde kalır.
  const yer = soz.yerlesim ?? SOZ.yerlesim;
  const yollar = [
    ["cd", "M319.5 319.5A169 169 0 1 1 319.5 80.5", "c"],
    ["ci", "M308.19 308.19A153 153 0 1 1 308.19 91.81", "ci"],
    ["da", "M159 200A41 41 0 0 1 241 200A71 71 0 0 0 383 200", "dalga"],
    ["db", "M143 200A57 57 0 0 1 257 200A55 55 0 0 0 367 200", "dalga"],
  ];
  return kor + `<svg class="s-cs__form" ${SVG}><defs>` +
    yollar.map(([id, d]) => `<path id="${uid}-${id}" d="${d}"/>`).join("") + `</defs><g class="s-cs__soz">` +
    yollar.map(([id, , k]) => `<text style="letter-spacing:${yer[k].ara}px"><textPath href="#${uid}-${id}">${tekrar(soz[k], yer[k].tekrar)}</textPath></text>`).join("") +
    "</g></svg>";
}

// Yeni biçim, sağ üstten sol alta kayan 45° çizginin arkasından gelir.
const giris = (c) => `polygon(${c}% 0%, ${c + 200}% 0%, ${c + 300}% 100%, ${c + 100}% 100%)`;
const cikis = (c) => `polygon(${c}% 0%, ${c + 100}% 100%, ${c - 300}% 100%, ${c - 300}% 0%)`;

export function baslat(bolum) {
  const doc = bolum.ownerDocument;
  kokuIsaretle(doc);
  const sahne = bolum.querySelector(".s-cs");
  const bicim = {};
  for (const f of sahne.querySelectorAll(".s-cs__bicim")) bicim[f.dataset.bicim] = f;
  const secici = bolum.querySelector(".s-cs__secici");
  const dugmeler = [...bolum.querySelectorAll(".s-cs__secici .c-dugme[data-bicim]")];
  const kesik = sahne.appendChild(doc.createElement("div"));
  kesik.className = "s-cs__kesik";
  kesik.setAttribute("aria-hidden", "true");
  kesik.innerHTML = '<svg viewBox="0 0 400 400" focusable="false"><line x1="0" y1="0" x2="400" y2="400"/></svg>';
  const cizgi = kesik.firstChild;

  let cur = "cizgi", anims = null, eski = null, adim = 0, zaman = 0, gorunur = false, bekci = null;
  bicim.cizgi.classList.add("s-acik", "s-etkin");
  sahne.classList.add("s-canli");

  function bitir() {
    if (!anims) return;
    anims.forEach((a) => a.cancel());
    anims = null;
    if (eski && eski !== bicim[cur]) eski.classList.remove("s-acik");
    eski = null;
  }

  function git(id) {
    if (id === cur || !bicim[id]) return;
    bitir();
    const e = bicim[cur], y = bicim[id];
    cur = id;
    e.classList.remove("s-etkin");
    y.classList.add("s-acik", "s-etkin");
    for (const b of dugmeler) {
      const bu = b.dataset.bicim === id;
      b.setAttribute("aria-pressed", String(bu));
      b.classList.toggle("c-dugme--ikincil", !bu);
    }
    if (hareketAzaltildi() || typeof y.animate !== "function") { e.classList.remove("s-acik"); return; }
    // fill:"forwards" son kareyi bitir() iptal edene kadar tutar: eski biçim gizlenmeden önce kırpılmamış görünmez.
    const a = y.querySelector(".s-cs__form").animate([{ clipPath: giris(100) }, { clipPath: giris(-100) }], GECIS);
    anims = [
      a,
      e.querySelector(".s-cs__form").animate([{ clipPath: cikis(100) }, { clipPath: cikis(-100) }], GECIS),
      cizgi.animate([{ transform: "translateX(100%)", opacity: 0.6 }, { transform: "translateX(-100%)", opacity: 0.6 }], GECIS),
    ];
    eski = e;
    a.onfinish = () => { if (anims && anims[0] === a) bitir(); };
  }

  // Tek tur: söze geç, bekle, çizgiye dön, dur. Ekran dışına çıkılıp dönülürse o adımın beklemesi baştan sayılır.
  function planla() {
    clearTimeout(zaman);
    if (adim >= TUR.length) { bekci?.(); bekci = null; return; }
    if (!gorunur || hareketAzaltildi()) return;
    zaman = setTimeout(() => { git(TUR[adim].id); adim++; planla(); }, TUR[adim].bekle);
  }

  const tikla = (ev) => {
    const b = ev.target.closest(".c-dugme[data-bicim]");
    if (!b) return;
    adim = TUR.length;   // elle seçince tur biter
    planla();
    git(b.dataset.bicim);
  };
  const uygula = (az) => {
    if (secici) secici.hidden = az;
    bitir();
    planla();
  };

  secici?.addEventListener("click", tikla);
  const birakAz = azaltmaIzle(uygula);
  uygula(hareketAzaltildi());
  bekci = gorunurlukBekcisi(sahne, {
    gir: () => { gorunur = true; planla(); },
    cik: () => { gorunur = false; planla(); },
  });

  return () => {
    clearTimeout(zaman);
    bitir();
    bekci?.();
    bekci = null;
    birakAz();
    secici?.removeEventListener("click", tikla);
    kesik.remove();
    sahne.classList.remove("s-canli");
  };
}
