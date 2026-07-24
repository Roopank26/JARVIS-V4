const puppeteer = require("puppeteer");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  const b = await puppeteer.launch({ headless: "new", args: ["--no-sandbox", "--disable-setuid-sandbox"] });
  const p = await b.newPage();
  const ce = [], pe = [];
  p.on("console", (m) => { if (m.type() === "error") ce.push(m.text()); });
  p.on("pageerror", (e) => pe.push(e.message));
  await p.setCacheEnabled(false);
  await p.goto("http://127.0.0.1:8742/", { waitUntil: "networkidle2", timeout: 30000 });
  await sleep(3000);

  const chatResult = await p.evaluate(async () => {
    buildChat();
    // pass plain objects that look like File results
    const files = [
      { name: "notes.txt", size: 11, type: "text/plain", result: "data:text/plain;base64,aGVsbG8gd29ybGQ=" },
      { name: "image.png", size: 1024, type: "image/png", result: "data:image/png;base64,iVBORw0KGgo=" },
    ];
    handleFiles(files);
    await sleep(100);
    const tray = document.getElementById("attachTray");
    return {
      hasTray: !!tray,
      chips: tray ? tray.querySelectorAll(".att-chip").length : 0,
      chipNames: tray ? [...tray.querySelectorAll(".att-name")].map((n) => n.textContent) : [],
      cardExists: !!document.querySelector("#view-chat .chat-card"),
    };
  });

  console.log("CHAT DND:", JSON.stringify(chatResult));
  console.log("consoleErrors:", JSON.stringify(ce));
  console.log("pageErrors:", JSON.stringify(pe));
  await b.close();
})();
