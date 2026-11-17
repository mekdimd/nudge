// All account data and actions on this recording page are fictitious.
const icon = (name) => '<img src="assets/icons/' + name + '.svg" alt="">';
const months = [
  {
    name: "October",
    short: "Oct",
    days: 31,
    opening: "2,956.81",
    incoming: "3,700.00",
    outgoing: "3,408.31",
    closing: "3,248.50",
  },
  {
    name: "September",
    short: "Sep",
    days: 30,
    opening: "2,713.94",
    incoming: "3,700.00",
    outgoing: "3,457.13",
    closing: "2,956.81",
  },
  {
    name: "August",
    short: "Aug",
    days: 31,
    opening: "2,580.62",
    incoming: "3,700.00",
    outgoing: "3,566.68",
    closing: "2,713.94",
  },
];
function bankNav(selected) {
  const items = [
    ["overview", "layout-dashboard", "Overview"],
    ["accounts", "wallet", "Accounts"],
    ["statements", "file-text", "Statements"],
    ["transfers", "arrow-left-right", "Transfers"],
    ["settings", "settings", "Settings"],
  ];
  nav.innerHTML =
    '<div class="bank-logo">' +
    icon("landmark") +
    '<span>Northline</span></div><p class="nav-label">Personal banking</p>' +
    items
      .map(
        ([id, glyph, label]) =>
          '<button id="' +
          id +
          '" class="' +
          (selected === id ? "active" : "") +
          '" ' +
          (selected === id ? 'aria-current="page"' : "") +
          ">" +
          icon(glyph) +
          "<span>" +
          label +
          "</span></button>",
      )
      .join("") +
    '<div class="nav-bottom"><button id="bank-support">' +
    icon("circle-help") +
    "<span>Help & support</span></button><p>Sample account<br>Fictitious data for this demo</p></div>";
  const handlers = {
    overview: bankOverview,
    accounts: bankAccounts,
    statements: bankStatements,
    transfers: bankTransfers,
    settings: bankSettings,
  };
  for (const [id, fn] of Object.entries(handlers))
    document.getElementById(id).onclick = fn;
  document.getElementById("bank-support").onclick = () =>
    bankDialog(
      "Help & support",
      "This sample page supports statement downloads and local account navigation. It does not connect to a bank.",
    );
}
const bankFooter =
  '<p class="page-footer">' +
  icon("lock-keyhole") +
  "Your session is secure</p>";
function bankStart() {
  document.body.classList.add("bank");
  if (new URLSearchParams(location.search).get("theme") === "light")
    document.body.dataset.theme = "light";
  document.getElementById("brand").textContent = "Personal banking";
  document.querySelector(".header-right").innerHTML =
    '<button class="icon-button" id="notifications" aria-label="Notifications">' +
    icon("bell") +
    '</button><span>Maya Bennett</span><span class="avatar">MB</span>';
  document.getElementById("notifications").onclick = () =>
    bankDialog("Notifications", "Your October statement is ready to download.");
  bankOverview();
}
function accountRows() {
  return (
    '<div class="account"><div class="account-mark">' +
    icon("wallet") +
    '</div><div><div class="account-name">Everyday chequing</div><div class="account-number">Account ending 4821</div></div><div class="amount">$3,248.50<small>CAD available</small></div></div><div class="account"><div class="account-mark savings">' +
    icon("piggy-bank") +
    '</div><div><div class="account-name">High interest savings</div><div class="account-number">Account ending 9063</div></div><div class="amount">$8,612.74<small>CAD available</small></div></div>'
  );
}
function bankOverview() {
  document.title = "Overview | Northline";
  bankNav("overview");
  content.innerHTML =
    '<h1>Good afternoon, Maya</h1><p class="sub">Welcome back to your personal banking.</p><div class="overview-top"><section class="account-card"><div class="card-title"><h2>Your accounts</h2><button class="text-button" id="all-accounts">View accounts</button></div>' +
    accountRows() +
    '</section><section class="quick-card"><h2>Manage your money</h2><div class="quick-row">' +
    icon("arrow-left-right") +
    '<div>Move money<small>Between your Northline accounts</small></div><button class="secondary" id="quick-transfer">Transfer</button></div><div class="quick-row">' +
    icon("file-text") +
    '<div>October statement<small>Everyday chequing ending 4821</small></div><button class="secondary" id="recent-statement">View statement</button></div></section></div><section class="activity"><div class="activity-tools"><h2>Recent transactions</h2><button class="text-button" id="all-transactions">View all transactions</button></div><table><thead><tr><th>Transaction</th><th>Date</th><th>Account</th><th>Amount</th></tr></thead><tbody><tr><td><div class="merchant"><span class="merchant-mark">WF</span><div>Whole Foods Market<small>Card purchase</small></div></div></td><td>Nov 14, 2026</td><td>Chequing • 4821</td><td>−$64.20</td></tr><tr><td><div class="merchant"><span class="merchant-mark" style="background:#e8f3eb">' +
    icon("arrow-down-left") +
    '</span><div>Payroll deposit<small>Direct deposit</small></div></div></td><td>Nov 13, 2026</td><td>Chequing • 4821</td><td class="positive">+$1,850.00</td></tr><tr><td><div class="merchant"><span class="merchant-mark">T</span><div>TELUS<small>Preauthorized payment</small></div></div></td><td>Nov 10, 2026</td><td>Chequing • 4821</td><td>−$79.00</td></tr><tr><td><div class="merchant"><span class="merchant-mark">C</span><div>Compass Card<small>Card purchase</small></div></div></td><td>Nov 9, 2026</td><td>Chequing • 4821</td><td>−$25.00</td></tr></tbody></table><div class="table-foot"><span>Showing your 4 most recent transactions</span><span>All amounts in CAD</span></div></section>' +
    bankFooter;
  document.getElementById("recent-statement").onclick = () => bankDetail(0);
  document.getElementById("all-accounts").onclick = bankAccounts;
  document.getElementById("all-transactions").onclick = bankAccounts;
  document.getElementById("quick-transfer").onclick = bankTransfers;
}
function bankStatements() {
  document.title = "Statements | Northline";
  bankNav("statements");
  content.innerHTML =
    '<h1>Statements</h1><p class="sub">Your monthly account statements, all in one place.</p><div class="filter-strip"><select aria-label="Account"><option>Everyday chequing • 4821</option></select><select aria-label="Statement year"><option>2026</option></select></div><section class="activity"><div class="activity-tools"><h2>Account statements</h2><span class="muted">PDF documents</span></div><table class="statements-table"><thead><tr><th>Statement</th><th>Period</th><th>Closing balance</th><th></th></tr></thead><tbody>' +
    months
      .map(
        (m, i) =>
          '<tr><td><div class="merchant"><span class="file-mark">' +
          icon("file-text") +
          '</span><div class="statement-title">' +
          m.name +
          " 2026<small>Everyday chequing</small></div></div></td><td>" +
          m.short +
          " 1 to " +
          m.short +
          " " +
          m.days +
          ", 2026</td><td>$" +
          m.closing +
          '</td><td><button class="secondary" id="month-' +
          i +
          '" aria-label="View ' +
          m.name +
          ' statement">View statement ' +
          icon("chevron-right") +
          "</button></td></tr>",
      )
      .join("") +
    '</tbody></table><div class="table-foot"><span>Statements available for this sample account</span><span>All amounts in CAD</span></div></section>' +
    bankFooter;
  months.forEach(
    (_, i) =>
      (document.getElementById("month-" + i).onclick = () => bankDetail(i)),
  );
}
function bankDetail(index) {
  const m = months[index];
  document.title = m.name + " 2026 statement | Northline";
  bankNav("statements");
  content.innerHTML =
    '<div class="crumb"><button class="text-button" id="back-statements">Statements</button>' +
    icon("chevron-right") +
    "<span>" +
    m.name +
    " 2026</span></div><h1>" +
    m.name +
    ' statement</h1><p class="sub">Everyday chequing ending 4821</p><div class="detail-grid"><section class="document-preview" aria-label="Statement preview"><div class="document-brand">Northline</div><div class="document-header"><div>Maya Bennett<br>Vancouver, BC<br>Canada</div><div>Everyday chequing<br>Account ending 4821<br>Currency CAD</div></div><h2>Account statement</h2><p>' +
    m.name +
    " 1 to " +
    m.name +
    " " +
    m.days +
    ', 2026</p><div class="document-summary"><div><span>Opening balance</span><span>$' +
    m.opening +
    "</span></div><div><span>Deposits and credits</span><span>+$" +
    m.incoming +
    "</span></div><div><span>Withdrawals and debits</span><span>−$" +
    m.outgoing +
    "</span></div><div><span>Closing balance</span><span>$" +
    m.closing +
    '</span></div></div><div class="document-note">This preview contains sample account data.<br>Download the PDF to view your statement.</div></section><section class="download-card"><h2>Statement details</h2><dl><dt>Account</dt><dd>Everyday chequing • 4821</dd><dt>Statement period</dt><dd>' +
    m.name +
    " 1 to " +
    m.days +
    ", 2026</dd><dt>File format</dt><dd>PDF document</dd><dt>Closing balance</dt><dd>$" +
    m.closing +
    ' CAD</dd></dl><button class="primary" id="download">' +
    icon("download") +
    'Download PDF</button><div id="toast" role="status"></div></section></div>' +
    bankFooter;
  document.getElementById("back-statements").onclick = bankStatements;
  document.getElementById("download").onclick = function () {
    const file = m.name + "-2026-statement.pdf";
    const a = document.createElement("a");
    a.href = "statements/" + file;
    a.download = file;
    a.click();
    this.innerHTML = icon("check") + "PDF downloaded";
    this.disabled = true;
    const toast = document.getElementById("toast");
    toast.className = "success";
    toast.textContent = file + " downloaded";
    document.title = m.name + " statement downloaded | Northline";
  };
}
function bankAccounts() {
  bankOverview();
  bankNav("accounts");
  document.title = "Accounts | Northline";
  content.querySelector("h1").textContent = "Your accounts";
  content.querySelector(".sub").textContent =
    "Balances and recent activity across your accounts.";
}
function bankTransfers() {
  document.title = "Transfers | Northline";
  bankNav("transfers");
  content.innerHTML =
    '<h1>Transfer money</h1><p class="sub">Move money between your sample accounts.</p><form class="settings-card" id="transfer-form"><h2>Between your accounts</h2><label>From<select><option>Everyday chequing • 4821</option></select></label><label>To<select><option>High interest savings • 9063</option></select></label><label>Amount in CAD<input type="number" min="0.01" max="3248.50" step="0.01" required placeholder="0.00"></label><button class="primary" type="submit">Preview transfer</button><p class="muted" style="margin-top:16px">This demo does not move real money.</p></form>';
  document.getElementById("transfer-form").onsubmit = (e) => {
    e.preventDefault();
    bankDialog(
      "Sample transfer",
      "No money was moved. This is a recording demo.",
    );
  };
}
function bankSettings() {
  document.title = "Settings | Northline";
  bankNav("settings");
  content.innerHTML =
    '<h1>Settings</h1><p class="sub">Your profile and statement preferences.</p><section class="settings-card"><h2>Profile</h2><dl><dt>Account holder</dt><dd>Maya Bennett</dd><dt>Statement delivery</dt><dd>Online statements</dd><dt>Location</dt><dd>Vancouver, BC</dd></dl></section>';
}
function bankDialog(title, text) {
  let d = document.getElementById("bank-dialog");
  if (d) d.remove();
  d = document.createElement("dialog");
  d.id = "bank-dialog";
  d.innerHTML =
    "<h2>" +
    title +
    '</h2><p style="margin:14px 0 22px;font-size:13px">' +
    text +
    '</p><button class="primary">Close</button>';
  document.body.appendChild(d);
  d.querySelector("button").onclick = () => d.close();
  d.showModal();
}
