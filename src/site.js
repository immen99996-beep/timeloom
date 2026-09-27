(function () {
"use strict";
const pad = n => String(n).padStart(2, "0");

// Country page: live local time, today's status, past rows dimmed, next holiday marked.
const clock = document.querySelector(".clock-now[data-tz]");
if (clock) {
  const tz = clock.dataset.tz;
  const fmt = new Intl.DateTimeFormat("en-GB", {timeZone: tz, weekday: "long", day: "numeric", month: "long", hour: "2-digit", minute: "2-digit", hourCycle: "h23"});
  const keyFmt = new Intl.DateTimeFormat("en-CA", {timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit"});
  const dowFmt = new Intl.DateTimeFormat("en-US", {timeZone: tz, weekday: "short"});
  const DOW = {Sun:0, Mon:1, Tue:2, Wed:3, Thu:4, Fri:5, Sat:6};
  const tick = () => {
    const now = new Date();
    const key = keyFmt.format(now).replace(/-/g, "");
    clock.querySelector(".js-clock").textContent = fmt.format(now);
    const hol = (window.HOLIDAYS || {})[key];
    const wk = (window.WEEKEND || [0, 6]).includes(DOW[dowFmt.format(now)]);
    const s = clock.querySelector(".js-status");
    s.className = "js-status badge " + (hol || wk ? "b-orange" : "b-green");
    s.textContent = hol ? "Public holiday: " + hol : wk ? "Weekend" : "Working day";
    let marked = false;
    document.querySelectorAll("tr[data-date]").forEach(tr => {
      const d = tr.dataset.date;
      tr.classList.toggle("past", d < key);
      const old = tr.querySelector(".tag.next");
      if (old) old.remove();
      if (!marked && d >= key) {
        marked = true;
        const t = document.createElement("span");
        t.className = "tag next b-blue";
        t.textContent = d === key ? "today" : "next";
        tr.lastElementChild.appendChild(t);
      }
    });
  };
  tick();
  setInterval(tick, 30000);
}

// Holiday index: filter by English or Korean name.
const filter = document.getElementById("countryFilter");
if (filter) {
  const links = [...document.querySelectorAll(".country-grid a")];
  filter.addEventListener("input", () => {
    const q = filter.value.trim().toLowerCase();
    links.forEach(a => { a.hidden = q && !a.dataset.name.includes(q); });
    document.querySelectorAll(".country-grid").forEach(g => {
      const any = [...g.children].some(a => !a.hidden);
      g.hidden = !any;
      g.previousElementSibling.hidden = !any;
    });
  });
}
})();
