// COUNCIL site: home page "Kurul Masası". A particle canvas behind five sections and a row of five seats that opens
// them. Loaded by site.js only where the canvas (#alan) is. Every text comes from the page: the section names from the
// seats, the roadmap statuses from the list (data-durumlar), the live replay lines from the lines the page already holds.
// Canvas colors are read from the root's custom properties (tokens.css); nothing here writes a color.
// Without this script (no .masa-js on the root) the five sections stack and read in order.

// "tamam,denemede,yolda,…" (yol haritası listesindeki durumlar) → halkanın altı parçasının durumu: 2 tamam, 1 denemede, 0 yolda.
// Altı değer yoksa hepsi yolda sayılır.
export function durumlar(liste) {
  const d = String(liste || "").split(",").map(x => ({ tamam: 2, denemede: 1 })[x.trim()] ?? 0);
  return d.length === 6 ? d : Array(6).fill(0);
}

export function baslat(doc = document) {
  const kok = doc.documentElement;
  if (!doc.getElementById("alan")) return;
  const azHareket = matchMedia("(prefers-reduced-motion: reduce)");
  // "dar" = üst-alt düzen (görsel üstte); CSS'teki aynı sorgu
  const dar = matchMedia("((max-width: 999px) or (max-aspect-ratio: 5/4)) and (not ((orientation: landscape) and (max-height: 560px) and (min-width: 560px)))");

  /* ================= parçacık alanı ================= */
  const tuval = doc.getElementById("alan");
  const masaEl = doc.querySelector(".masa");
  const c = tuval.getContext("2d");
  let W = 0, H = 0, DPR = 1, N = 0, P = [], renk = [], bicim = "amblem", vurgu = -1, vurguN = 1, perde = 1, DURUM = Array(6).fill(0);
  const fare = { x: -9999, y: -9999 };
  let paket = [], dalga = [], parlama = []; // canlı sahnedeki aktarım: yol alan parçacık sürüsü, hafızada halka dalgası, cihazda kor parlama
  const isaret = new Uint8Array(4096); // ağ biçiminde hangi parçacık hangi cihazın simgesinde (j + 1)

  function renkleriOku() {
    const s = getComputedStyle(kok);
    renk = ["--murekkep", "--kor", "--murekkep-3", "--kor-metin", "--zemin", "--basari", "--uyari"].map(v => s.getPropertyValue(v).trim());
  }
  function yerlesim() {
    if (dar.matches) { // üstteki bant: 64 px'ten ekranın %32+84 px'ine kadar
      const ust = 64, alt = H * .32 + 84, bant = alt - ust;
      return { cx: W * .5, cy: ust + bant * .52, R: Math.min(W * .3, bant * .4) };
    }
    // yan düzen: yazı sütununun sağında, koltuk yayına (altta ~118 px) çarpmadan
    const yaziSag = Math.max(28, W * .07) + Math.min(540, W * .44) + 24;
    const cy = (64 + (H - 118)) / 2;
    let R = Math.min(H * .34, W * .22, (H - 182) / 2.3);
    const cx = Math.min(W - R * .95, Math.max(W * .7, yaziSag + R * 1.25));
    return { cx, cy, R };
  }
  // tek tip rastgele, ama her yüklemede aynı (sahne tekrarlanabilir dursun)
  let tohum = 7;
  const rnd = () => (tohum = (tohum * 16807) % 2147483647) / 2147483647;

  // amblem geometrisi (400 birimlik kutu, merkez 0,0; dış halka r=168)
  function sDist(x, y) {
    const a = y <= 0 ? Math.abs(Math.hypot(x, y) - 56) : Math.min(Math.hypot(x + 56, y), Math.hypot(x - 56, y));
    const b = y >= 0 ? Math.abs(Math.hypot(x - 112, y) - 56) : Math.min(Math.hypot(x - 56, y), Math.hypot(x - 168, y));
    return Math.min(a, b);
  }
  function amblemNoktasi(k, ko = 1) {
    // k: 0 dış yay, 1 kor halka, 2 S eğrisi; ko: çizgi kalınlığı çarpanı
    const kal = (rnd() - .5) * 26 * ko;
    if (k === 0) { const t = (45 + rnd() * 270) * Math.PI / 180; const r = 168 + kal; return [Math.cos(t) * r, Math.sin(t) * r, 0]; }
    if (k === 1) { for (;;) { const t = rnd() * Math.PI * 2; const r = 112 + kal; const x = Math.cos(t) * r, y = Math.sin(t) * r; if (sDist(x, y) > 25) return [x, y, 1]; } }
    const u = rnd();
    if (u < .5) { const t = Math.PI + u * 2 * Math.PI; const r = 56 + kal; return [Math.cos(t) * r, Math.sin(t) * r, 0]; }
    const t = Math.PI - (u - .5) * 2 * Math.PI; const r = 56 + kal; return [112 + Math.cos(t) * r, Math.sin(t) * r, 0];
  }
  function amblem(L, olcek = 1, ox = 0, oy = 0) {
    const s = L.R / 168 * olcek, out = [];
    for (let i = 0; i < N; i++) {
      const u = i / N;
      if (u < .86) {
        const k = u < .4 ? 0 : u < .76 ? 1 : 2;
        const [x, y, cc] = amblemNoktasi(k);
        out.push([L.cx + ox + x * s, L.cy + oy + y * s, cc, cc === 1 ? .95 : .85]);
      } else { // toz: halkanın çevresinde seyrek parıltı
        const t = rnd() * Math.PI * 2, r = L.R * (1.1 + Math.pow(rnd(), 1.7) * 1.4) * olcek;
        out.push([L.cx + ox + Math.cos(t) * r, L.cy + oy + Math.sin(t) * r, 2, .15 + rnd() * .35]);
      }
    }
    return out;
  }
  const BICIM = {
    amblem: (L) => amblem(L),
    ag: (L) => {
      const out = [], d = yerler(L);
      for (let i = 0; i < N; i++) {
        const u = i / N, kal = (rnd() - .5);
        if (i < isaret.length) isaret[i] = 0;
        if (u < .32) { // ortada hafıza: küçük bir amblem, aynı parçacıklardan
          const u2 = u / .32, [x, y, cc] = amblemNoktasi(u2 < .42 ? 0 : u2 < .8 ? 1 : 2, .6), sk = L.R / 168 * .42;
          out.push([d.m[0] + x * sk, d.m[1] + y * sk, cc, cc === 1 ? .95 : .85]); }
        else if (u < .62) { // cihazlar: simge çizgileri parçacıkla çizilir
          const j = i % 3, n = d.n[j], [x, y] = simgeNoktasi(CIHAZ[j]), sk = L.R * .3 / 24;
          isaret[i] = j + 1;
          out.push([n[0] + (x - 12) * sk, n[1] + (y - 12) * sk, 0, .9]); continue; }
        else if (u < .86) { const [x, y] = yolNoktasi(yol(L, i % 3), rnd()); out.push([x + kal * 2.4, y + kal * 2.4, 2, .3]); }
        else { const t = rnd() * 6.283, r = L.R * (1.5 + rnd() * 1.2); out.push([d.m[0] + Math.cos(t) * r, d.m[1] + Math.sin(t) * r, 2, .12 + rnd() * .2]); }
      }
      return out;
    },
    dongu: (L, z) => {
      const out = [];
      for (let i = 0; i < N; i++) {
        const u = i / N, kal = (rnd() - .5);
        if (u < .84) { const t0 = (i * 2.399) % 6.283, t = t0 + z * .00018, r = L.R * .95 + kal * L.R * .16;
          const yakin = [-Math.PI / 2, Math.PI / 6, 5 * Math.PI / 6].findIndex((d, j) => Math.abs(Math.atan2(Math.sin(t - d), Math.cos(t - d))) < .2 && (vurgu < 0 || vurgu === j));
          out.push([L.cx + Math.cos(t) * r, L.cy + Math.sin(t) * r, yakin >= 0 ? DURAK_RENK[yakin] : 0, yakin >= 0 ? 1 : .45]); }
        else { const t = rnd() * 6.283, r = L.R * (1.25 + rnd() * 1.3); out.push([L.cx + Math.cos(t) * r, L.cy + Math.sin(t) * r, 2, .12 + rnd() * .2]); }
      }
      return out;
    },
    kurul: (L) => {
      const out = [], durum = DURUM; // 2 tamam, 1 denemede, 0 yolda (yol haritası listesinden)
      for (let i = 0; i < N; i++) {
        const u = i / N, kal = (rnd() - .5);
        if (u < .72) {
          const p = i % 6, d = durum[p];
          const t = (-90 + p * 60 + 5 + rnd() * 50) * Math.PI / 180, r = L.R * .86 + kal * L.R * .15;
          const parlak = vurgu < 0 ? 1 : (p >= vurgu && p < vurgu + vurguN) ? 1.25 : .45;
          if (d === 0 && rnd() < .55) { out.push([L.cx + Math.cos(t) * r, L.cy + Math.sin(t) * r, 2, .22 * parlak]); continue; }
          out.push([L.cx + Math.cos(t) * r, L.cy + Math.sin(t) * r, d ? 1 : 2, (d === 2 ? .95 : d === 1 ? .6 : .4) * parlak]);
        } else {
          const u2 = (u - .72) / .28, [x, y, cc] = amblemNoktasi(u2 < .42 ? 0 : u2 < .8 ? 1 : 2, .55); const s = L.R / 168 * .5;
          out.push([L.cx + x * s, L.cy + y * s, cc, .7]);
        }
      }
      return out;
    },
    yorunge: (L, z) => {
      const out = [], egim = -.32;
      for (let i = 0; i < N; i++) {
        const u = i / N;
        if (u < .88) {
          const k = i % 4, r = L.R * (.45 + k * .26), hiz = (4 - k) * .00006 + .00003;
          const t = (i * 2.399) % 6.283 + z * hiz, kal = (rnd() - .5) * 1.6;
          const x = Math.cos(t) * r, y = Math.sin(t) * r * .5;
          const gez = ((i * 7) % 97) < 3; // her yörüngede birkaç parlak "gezegen"
          out.push([L.cx + x * Math.cos(egim) - y * Math.sin(egim) + kal, L.cy + x * Math.sin(egim) + y * Math.cos(egim) + kal, gez ? 1 : (k === 0 ? 0 : 2), gez ? 1 : .55]);
        } else { const t = rnd() * 6.283, r = L.R * .16 * Math.sqrt(rnd()); out.push([L.cx + Math.cos(t) * r, L.cy + Math.sin(t) * r, 1, .9]); }
      }
      return out;
    },
  };
  const DEVINGEN = new Set(["dongu", "yorunge"]);
  const DURAK_RENK = [5, 6, 1]; // okur: başarı yeşili, alır: uyarı sarısı, yazar: kor (listedeki numaralar aynı renkte)
  // cihazla hafıza arasındaki yol: simgenin kenarından amblemin kenarına hafif kavisli bir eğri
  function yol(L, j) {
    const d = yerler(L), n = d.n[j], m = d.m, dx = m[0] - n[0], dy = m[1] - n[1], uz = Math.hypot(dx, dy), ux = dx / uz, uy = dy / uz;
    const a = [n[0] + ux * L.R * .24, n[1] + uy * L.R * .24], b = [m[0] - ux * L.R * .5, m[1] - uy * L.R * .5];
    return { a, b, k: [(a[0] + b[0]) / 2 - uy * uz * .14, (a[1] + b[1]) / 2 + ux * uz * .14], ux, uy };
  }
  const yolNoktasi = (e, f) => [(1 - f) * (1 - f) * e.a[0] + 2 * (1 - f) * f * e.k[0] + f * f * e.b[0], (1 - f) * (1 - f) * e.a[1] + 2 * (1 - f) * f * e.k[1] + f * f * e.b[1]];
  function yerler(L) {
    const m = [L.cx, L.cy], d = L.R * 1.2;
    return { m, n: [[m[0] + Math.cos(-2.4) * d, m[1] + Math.sin(-2.4) * d], [m[0] + Math.cos(2.4) * d, m[1] + Math.sin(2.4) * d], [Math.min(m[0] + d * 1.02, W - L.R * .14 - 48), m[1]]] };
  }

  let hedef = [];
  function hedefKur(z = 0) {
    tohum = 7 + (bicim.length * 31);
    hedef = BICIM[bicim](yerlesim(), z);
  }
  function boyut() {
    DPR = Math.min(window.devicePixelRatio || 1, 2);
    W = innerWidth; H = innerHeight;
    tuval.width = W * DPR; tuval.height = H * DPR;
    c.setTransform(DPR, 0, 0, DPR, 0, 0);
    const yeniN = dar.matches ? 1400 : 3000;
    if (yeniN !== N) {
      N = yeniN; tohum = 3;
      P = Array.from({ length: N }, () => ({ x: W * rnd(), y: H * rnd(), vx: 0, vy: 0, a: 0, c: 2 }));
    }
    hedefKur(performance.now());
    // masaüstünde koltuk yayı amblemin altında durur; telefonda ortada
    masaEl.style.left = dar.matches ? "" : Math.round(yerlesim().cx) + "px";
    if (azHareket.matches) yapistir();
  }
  function yapistir() {
    for (let i = 0; i < N; i++) { const h = hedef[i], p = P[i]; p.x = h[0]; p.y = h[1]; p.c = h[2]; p.a = h[3]; }
    ciz(0);
  }
  // ağdaki cihazlar sayfanın simgeleriyle (brand/simge, 24 birim) aynı çizgilerden, parçacıkla kurulur
  const CIZGI = {
    telefon: [[6, 3, 18, 3], [6, 21, 18, 21], [7, 3, 7, 21], [17, 3, 17, 21], [10, 18, 14, 18]],
    bilgisayar: [[2, 4, 22, 4], [2, 16, 22, 16], [3, 4, 3, 16], [21, 4, 21, 16], [12, 16, 12, 20], [8, 20, 16, 20]],
    sunucu: [[3, 3, 21, 3], [3, 10, 21, 10], [4, 3, 4, 10], [20, 3, 20, 10], [3, 14, 21, 14], [3, 21, 21, 21], [4, 14, 4, 21], [20, 14, 20, 21], [7, 6.5, 9, 6.5], [7, 17.5, 9, 17.5]],
  };
  const CIHAZ = ["telefon", "bilgisayar", "sunucu"];
  const TOPLAM = Object.fromEntries(Object.entries(CIZGI).map(([ad, l]) => [ad, l.reduce((t, [a, b, c2, d2]) => t + Math.hypot(c2 - a, d2 - b), 0)]));
  function simgeNoktasi(ad) {
    let k = rnd() * TOPLAM[ad];
    for (const [a, b, c2, d2] of CIZGI[ad]) {
      const uz = Math.hypot(c2 - a, d2 - b);
      if (k <= uz) { const f = k / uz, j = (rnd() - .5) * 1.4; return [a + (c2 - a) * f + (b === d2 ? 0 : j), b + (d2 - b) * f + (b === d2 ? j : 0)]; }
      k -= uz;
    }
    return [12, 12];
  }
  function ciz(z) {
    c.clearRect(0, 0, W, H);
    const boy = dar.matches ? 1.5 : 1.7;
    // cihaz parlaması: simgenin parçacıkları bir an kor yanar, sonra söner
    const pl = [0, 0, 0];
    parlama = parlama.filter(q => z - q.t0 < 1100);
    for (const q of parlama) pl[q.j] = Math.max(pl[q.j], 1 - (z - q.t0) / 1100);
    const agda = bicim === "ag";
    for (const k of [0, 1, 2, 5, 6]) {
      c.fillStyle = renk[k];
      for (let i = 0; i < N; i++) {
        const p = P[i]; if (p.a < .02) continue;
        const fl = agda && isaret[i] ? pl[isaret[i] - 1] : 0;
        if (p.c === k) { c.globalAlpha = Math.min(1, p.a) * perde * (1 - fl); c.fillRect(p.x, p.y, boy, boy); }
        else if (k === 1 && fl > 0) { c.globalAlpha = fl * perde; c.fillRect(p.x - .4, p.y - .4, boy + .8, boy + .8); }
      }
    }
    if (agda && (paket.length || dalga.length)) {
      const L = yerlesim(), d = yerler(L);
      // yol alan sürü: 34 parçacık kavisli yol boyunca akar, baştakiler parlak ve iri, kuyruk söner
      c.fillStyle = renk[3];
      paket = paket.filter(q => z - q.t0 < q.sure + 600);
      for (const q of paket) {
        const e = yol(L, q.j), f = (z - q.t0) / q.sure;
        if (f >= 1 && !q.vardi) { q.vardi = true; if (q.yon > 0) dalga.push({ t0: z }); else parlama.push({ j: q.j, t0: z }); }
        for (let s = 0; s < 34; s++) {
          const g = f - s * .014; if (g < 0 || g > 1) continue;
          const kol = g < .5 ? 2 * g * g : 1 - Math.pow(-2 * g + 2, 2) / 2, yer = q.yon > 0 ? kol : 1 - kol;
          const [x, y] = yolNoktasi(e, yer), sap = Math.sin(s * 2.1 + z * .012) * (2 + s * .12);
          const boyut2 = Math.max(1.2, 3.4 - s * .07);
          c.globalAlpha = (1 - s / 34) * perde;
          c.fillRect(x - e.uy * sap - boyut2 / 2, y + e.ux * sap - boyut2 / 2, boyut2, boyut2);
        }
      }
      // hafızaya yazıldı: amblemin çevresinden genişleyen kesik bir halka
      dalga = dalga.filter(q => z - q.t0 < 900);
      for (const q of dalga) {
        const f = (z - q.t0) / 900, rr = L.R * (.48 + f * .42);
        c.globalAlpha = (1 - f) * perde;
        for (let a = 0; a < 72; a++) { if (a % 6 === 5) continue; const t = a / 72 * 6.283; c.fillRect(d.m[0] + Math.cos(t) * rr - 1.2, d.m[1] + Math.sin(t) * rr - 1.2, 2.4, 2.4); }
      }
    }
    c.globalAlpha = 1;
  }
  let son = 0;
  function dongu(z) {
    if (doc.hidden) { son = 0; requestAnimationFrame(dongu); return; }
    if (DEVINGEN.has(bicim) && z - son > 33) { hedefKur(z); son = z; }
    const k = .05, sur = .8, fr = 110 * 110;
    for (let i = 0; i < N; i++) {
      const p = P[i], h = hedef[i];
      let ax = (h[0] - p.x) * k, ay = (h[1] - p.y) * k;
      const dx = p.x - fare.x, dy = p.y - fare.y, d2 = dx * dx + dy * dy;
      if (d2 < fr) { const g = (1 - d2 / fr) * 2.6 / Math.sqrt(d2 + 1); ax += dx * g; ay += dy * g; }
      p.vx = (p.vx + ax) * sur; p.vy = (p.vy + ay) * sur;
      p.x += p.vx + Math.sin(z * .0011 + i) * .12; p.y += p.vy + Math.cos(z * .0013 + i * 1.7) * .12;
      p.a += (h[3] - p.a) * .06;
      if (Math.abs(h[0] - p.x) < 40) p.c = h[2];
    }
    ciz(z);
    requestAnimationFrame(dongu);
  }
  function bicimDegis(yeni, yeniPerde) {
    bicim = yeni; vurgu = -1; perde = yeniPerde;
    hedefKur(performance.now());
    if (azHareket.matches) yapistir();
  }
  // kimden/kime: cihaz sırası (0 telefon, 1 bilgisayar, 2 sunucu) ya da "m" (hafıza)
  function aktar(kimden, kime) {
    if (azHareket.matches) return;
    const z = performance.now(), j = kimden === "m" ? kime : kimden, yon = kimden === "m" ? -1 : 1;
    if (yon > 0) parlama.push({ j, t0: z }); // gönderen cihaz yanar, sürü yola çıkar
    paket.push({ j, yon, t0: z + (yon > 0 ? 250 : 0), sure: 1300 });
  }
  addEventListener("pointermove", e => { fare.x = e.clientX; fare.y = e.clientY; }, { passive: true });
  addEventListener("pointerleave", () => { fare.x = fare.y = -9999; });
  doc.addEventListener("pointerout", e => { if (!e.relatedTarget) fare.x = fare.y = -9999; });
  addEventListener("resize", boyut);
  renkleriOku(); boyut();
  new MutationObserver(() => { renkleriOku(); if (azHareket.matches) ciz(0); }).observe(kok, { attributes: true, attributeFilter: ["data-theme"] });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", renkleriOku);
  if (azHareket.matches) yapistir(); else requestAnimationFrame(dongu);


  /* ================= sahneler ================= */
  const sekmeler = [...doc.querySelectorAll(".masa [role=tab]")];
  const ADLAR = sekmeler.map(s => s.querySelector(".gizli").textContent.trim());
  const masaAd = doc.getElementById("masa-ad"), masaIz = doc.querySelector(".masa__kenar .iz");
  const etiket = i => { masaAd.textContent = ADLAR[i]; };
  masaIz.style.strokeDasharray = "100 100";
  const sahneler = sekmeler.map(s => doc.getElementById(s.getAttribute("aria-controls")));
  const kapanis = () => parseFloat(getComputedStyle(kok).getPropertyValue("--sure-sahne")) || 420; // ms
  let simdi = 0, kilit = 0;
  // Kapanan bölüm solarak çıkar, sonra `hidden` olur: seçili olmayan sekme panelleri okunmaz, odak almaz.
  function kapat(s) {
    s.removeAttribute("data-acik");
    clearTimeout(s._gizle);
    s._gizle = setTimeout(() => { if (!s.hasAttribute("data-acik")) s.hidden = true; }, azHareket.matches ? 0 : kapanis() + 60);
  }
  function ac(s) {
    clearTimeout(s._gizle);
    s.hidden = false; s.scrollTop = 0;
    s.getBoundingClientRect(); // gizli ilk hâli uygula, sonra aç
    s.setAttribute("data-acik", "");
  }
  function git(i, odak) {
    i = Math.max(0, Math.min(sahneler.length - 1, i));
    if (i === simdi && sahneler[i].hasAttribute("data-acik")) { if (odak) sekmeler[i].focus(); return; }
    kapat(sahneler[simdi]);
    sekmeler[simdi].setAttribute("aria-selected", "false"); sekmeler[simdi].tabIndex = -1;
    simdi = i;
    const s = sahneler[i];
    ac(s);
    sekmeler[i].setAttribute("aria-selected", "true"); sekmeler[i].tabIndex = 0;
    if (odak) sekmeler[i].focus();
    etiket(i); masaIz.style.strokeDashoffset = String(100 - i * 25);
    bicimDegis(s.dataset.bicim, 1);
    try { history.replaceState(null, "", "#" + s.id); } catch (_) { /* adres çubuğu güncellenemezse bölüm yine açılır */ }
    if (s.dataset.bicim === "ag") oynat(); else durdur();
  }
  sekmeler.forEach((s, i) => {
    s.addEventListener("click", () => git(i));
    s.addEventListener("pointerenter", () => etiket(i)); s.addEventListener("pointerleave", () => etiket(simdi));
    s.addEventListener("focus", () => etiket(i)); s.addEventListener("blur", () => etiket(simdi));
  });
  doc.querySelector(".masa").addEventListener("keydown", e => {
    const ileri = ["ArrowDown", "ArrowRight"], geri = ["ArrowUp", "ArrowLeft"];
    if (ileri.includes(e.key)) { e.preventDefault(); git(simdi + 1, true); }
    else if (geri.includes(e.key)) { e.preventDefault(); git(simdi - 1, true); }
    else if (e.key === "Home") { e.preventDefault(); git(0, true); }
    else if (e.key === "End") { e.preventDefault(); git(sahneler.length - 1, true); }
  });
  // Üstteki yazı ana sayfaya bağlıdır; bu sayfadayken açılış bölümüne döner.
  doc.querySelector(".s-logo")?.addEventListener("click", e => { e.preventDefault(); git(0); });
  // masaüstünde tekerlek bir sahne ileri/geri götürür (sahnenin kendi kaydırması bitmişse)
  addEventListener("wheel", e => {
    if (dar.matches || Math.abs(e.deltaY) < 12) return;
    const s = sahneler[simdi], asagi = e.deltaY > 0;
    const bitti = asagi ? s.scrollTop + s.clientHeight >= s.scrollHeight - 2 : s.scrollTop <= 0;
    if (!bitti) return;
    const z = performance.now(); if (z < kilit) return;
    kilit = z + 900; git(simdi + (asagi ? 1 : -1));
  }, { passive: true });
  addEventListener("keydown", e => {
    if (e.target.closest("input, textarea, select, button, a, summary, [role=tablist]") || e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.key === "PageDown" || (e.key === " " && !e.shiftKey)) { e.preventDefault(); git(simdi + 1); }
    if (e.key === "PageUp" || (e.key === " " && e.shiftKey)) { e.preventDefault(); git(simdi - 1); }
    if (/^[1-5]$/.test(e.key)) git(+e.key - 1);
  });
  // listelerde üzerine gelinen satır halkada parlar (data-i: ilk parça, data-n: kaç parça)
  doc.querySelectorAll("[data-dongu] li, [data-kurul] li").forEach(li => {
    const on = () => { vurgu = +li.dataset.i; vurguN = +(li.dataset.n || 1); li.setAttribute("data-vurgu", ""); hedefKur(performance.now()); if (azHareket.matches) yapistir(); };
    const off = () => { vurgu = -1; li.removeAttribute("data-vurgu"); hedefKur(performance.now()); if (azHareket.matches) yapistir(); };
    li.addEventListener("pointerenter", on); li.addEventListener("pointerleave", off);
  });
  DURUM = durumlar(doc.querySelector("[data-durumlar]")?.dataset.durumlar);
  hedefKur(performance.now());
  if (azHareket.matches) yapistir();

  /* ================= canlı oynatma ================= */
  // Sayfa konuşmanın son hâlini yazılı taşır (betiksiz de okunur); betik satırları oradan okur, kutuyu boşaltır ve yeniden oynatır.
  const SATIRLAR = [...doc.querySelectorAll("#ekran-a .satir, #ekran-b .satir")];
  const BEKLE = [600, 500, 300, 1400, 500, 600, 700, 0]; // her satırdan sonra ms
  const AKTAR = { 2: [0, "m"], 4: ["m", 1], 6: ["m", 1] }; // satır sırası → [kimden, kime]: cihaz sırası ya da "m" (hafıza)
  const SENARYO = SATIRLAR.map((p, i) => ({ kutu: p.parentElement, tur: [...p.classList].find(k => k !== "satir"), p, metin: p.textContent, bekle: BEKLE[i], gec: AKTAR[i] }));
  let zaman = [];
  const durum = doc.getElementById("durum"), durumYazi = durum.querySelector("span"), durumHalka = durum.querySelector(".c-halka");
  function durumKur(calisiyor) {
    if (calisiyor) { durum.setAttribute("data-calisiyor", ""); durumHalka.style.setProperty("--deger", ".3"); durumYazi.textContent = durum.dataset.metinCalisiyor; }
    else { durum.removeAttribute("data-calisiyor"); durumHalka.style.setProperty("--deger", "1"); durumYazi.textContent = durum.dataset.metinBitti; }
  }
  function durdur() { zaman.forEach(clearTimeout); zaman = []; }
  function oynat() {
    durdur();
    for (const k of new Set(SENARYO.map(s => s.kutu))) k.textContent = "";
    if (azHareket.matches) { SENARYO.forEach(s => s.kutu.appendChild(s.p.cloneNode(true))); durumKur(false); return; }
    durumKur(true);
    let t = 500;
    const imlec = doc.createElement("span"); imlec.className = "imlec";
    SENARYO.forEach(({ kutu, tur, p: kaynak, metin, bekle, gec }) => {
      zaman.push(setTimeout(() => {
        if (tur === "sen" || tur === "yardimci") {
          const p = kaynak.cloneNode(false); p.textContent = ""; kutu.appendChild(p); let i = 0; const hiz = tur === "sen" ? 26 : 14;
          const yaz = () => { p.textContent = metin.slice(0, ++i); p.appendChild(imlec); if (i < metin.length) zaman.push(setTimeout(yaz, hiz)); else imlec.remove(); };
          yaz();
        } else kutu.appendChild(kaynak.cloneNode(true));
        if (gec) aktar(...gec);
      }, t));
      t += (tur === "sen" ? metin.length * 26 : tur === "yardimci" ? metin.length * 14 : 0) + bekle + 350;
    });
    zaman.push(setTimeout(() => durumKur(false), t));
  }
  doc.getElementById("yeniden").addEventListener("click", oynat);
  doc.getElementById("yeniden").hidden = false;
  // üst-alt düzende bölüm kaydırılınca görsel, üstüne gelen yazının arkasında söner
  sahneler.forEach((s, i) => s.addEventListener("scroll", () => {
    if (!dar.matches || simdi !== i) return;
    perde = Math.max(.18, 1 - s.scrollTop / 240);
    if (azHareket.matches) ciz(0);
  }, { passive: true }));

  /* başlangıç: adres çubuğundaki bölüm; öteki bölümler kapalı (hidden) */
  sahneler.forEach((s, i) => { if (i > 0) s.hidden = true; });
  const ilk = sahneler.findIndex(s => "#" + s.id === location.hash);
  if (ilk > 0) git(ilk); else { bicimDegis("amblem", 1); etiket(0); masaIz.style.strokeDashoffset = "100"; }
  // döndürme ya da pencere boyutu düzeni değiştirince görseli yeniden yerleştir
  dar.addEventListener("change", () => { boyut(); sahneler[simdi].scrollTop = 0; bicimDegis(sahneler[simdi].dataset.bicim, 1); });
  const azBasta = azHareket.matches;
  azHareket.addEventListener("change", () => { if (azHareket.matches !== azBasta) location.reload(); });
  kok.classList.add("masa-js"); // son iş: buraya kadar bir hata olursa sayfa betiksiz hâliyle okunur kalır
}
