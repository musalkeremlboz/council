// COUNCIL site: page boot. The measuring hook (?denetim=1) starts first so it sees the identity moment build the logo;
// then the identity moment (once per session; without JS or with reduced motion the page stays as written).
import { denetimKur } from "./denetim.js";
import { baslat as yaziKur } from "./sahne/yazi-kur.js";

denetimKur(document);
yaziKur(document);
